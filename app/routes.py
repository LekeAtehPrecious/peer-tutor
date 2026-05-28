from flask import (Blueprint, render_template, redirect,
                   url_for, request, flash)
from flask_login import (login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import (generate_password_hash,
                                check_password_hash)
from app import db
from app.models import (User, TutoringRequest, 
                        Session, Message, Rating)

# Create Blueprint
main = Blueprint("main", __name__)


@main.route("/")
def home():
    """Home page."""
    # Get latest real ratings to show on home page
    from app.models import Rating
    latest_ratings = Rating.query.filter(
        Rating.review != None,
        Rating.review != ""
    ).order_by(
        Rating.created_at.desc()).limit(3).all()

    # If no ratings with reviews get all ratings
    if not latest_ratings:
        latest_ratings = Rating.query.order_by(
            Rating.created_at.desc()).limit(3).all()

    return render_template(
        "home.html",
        latest_ratings=latest_ratings
    )

@main.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        existing_user = User.query.filter_by(
            email=email).first()
        if existing_user:
            flash("Email already registered.", "danger")
            return redirect(url_for("main.register"))

        hashed_password = generate_password_hash(password)
        new_user = User(
            full_name=full_name,
            email=email,
            password=hashed_password,
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please login.",
              "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    """Login an existing user."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(
                user.password, password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("main.login"))

        login_user(user)
        flash(f"Welcome back, {user.full_name}!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("login.html")


@main.route("/logout")
@login_required
def logout():
    """Logout current user."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))


@main.route("/dashboard")
@login_required
def dashboard():
    """User dashboard."""
    if current_user.role == "student":
        my_requests = TutoringRequest.query.filter_by(
            student_id=current_user.id).all()
        open_requests = TutoringRequest.query.filter_by(
            status="open").all()

        # Get session info for each request
        request_sessions = {}
        for req in my_requests:
            session = Session.query.filter_by(
                request_id=req.id).first()
            if session:
                request_sessions[req.id] = session

        return render_template(
            "dashboard.html",
            requests=my_requests,
            open_requests=open_requests,
            accepted_requests=[],
            request_sessions=request_sessions
        )
    else:
        open_requests = TutoringRequest.query.filter_by(
            status="open").all()

        my_sessions = Session.query.filter_by(
            tutor_id=current_user.id).all()

        accepted_requests = []
        for session in my_sessions:
            req = TutoringRequest.query.get(
                session.request_id)
            if req:
                accepted_requests.append({
                    "session": session,
                    "req": req
                })

        return render_template(
            "dashboard.html",
            open_requests=open_requests,
            accepted_requests=accepted_requests,
            requests=[],
            request_sessions={}
        )


@main.route("/request/new", methods=["GET", "POST"])
@login_required
def new_request():
    """Post a new tutoring request."""
    if current_user.role != "student":
        flash("Only students can post requests.", "danger")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        subject = request.form.get("subject")
        topic = request.form.get("topic")
        description = request.form.get("description")

        new_req = TutoringRequest(
            subject=subject,
            topic=topic,
            description=description,
            student_id=current_user.id
        )
        db.session.add(new_req)
        db.session.commit()
        flash("Request posted successfully!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("new_request.html")


@main.route("/request/<int:request_id>/accept",
            methods=["GET", "POST"])
@login_required
def accept_request(request_id):
    """Tutor accepts a tutoring request."""
    if current_user.role != "tutor":
        flash("Only tutors can accept requests.", "danger")
        return redirect(url_for("main.dashboard"))

    tutoring_request = TutoringRequest.query.get_or_404(
        request_id)

    if tutoring_request.status != "open":
        flash("This request is no longer available.",
              "danger")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        scheduled_time_str = request.form.get(
            "scheduled_time")
        from datetime import datetime
        scheduled_time = datetime.strptime(
            scheduled_time_str, "%Y-%m-%dT%H:%M")

        tutoring_request.status = "accepted"

        new_session = Session(
            scheduled_time=scheduled_time,
            status="upcoming",
            request_id=tutoring_request.id,
            tutor_id=current_user.id
        )
        db.session.add(new_session)
        db.session.commit()

        flash("Request accepted! Session has been scheduled.",
              "success")
        return redirect(url_for("main.dashboard"))

    return render_template(
        "accept_request.html",
        tutoring_request=tutoring_request
    )


@main.route("/chat/<int:session_id>",
            methods=["GET", "POST"])
@login_required
def chat(session_id):
    """Chat between student and tutor for a session."""
    session = Session.query.get_or_404(session_id)
    tutoring_request = TutoringRequest.query.get(
        session.request_id)

    # Check if user is allowed in this chat
    if (current_user.id != session.tutor_id and
            current_user.id != tutoring_request.student_id):
        flash("You are not allowed in this chat.", "danger")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        content = request.form.get("content")
        if content and content.strip():
            new_message = Message(
                content=content.strip(),
                sender_id=current_user.id,
                session_id=session_id
            )
            db.session.add(new_message)
            db.session.commit()
        return redirect(url_for("main.chat",
                                session_id=session_id))

    messages = Message.query.filter_by(
        session_id=session_id).order_by(
        Message.timestamp.asc()).all()

    other_user = (
        tutoring_request.student
        if current_user.id == session.tutor_id
        else session.tutor
    )

    return render_template(
        "chat.html",
        session=session,
        messages=messages,
        tutoring_request=tutoring_request,
        other_user=other_user
    )


@main.route("/session/<int:session_id>/complete",
            methods=["GET", "POST"])
@login_required
def complete_session(session_id):
    """Mark a session as complete and rate the tutor."""
    session = Session.query.get_or_404(session_id)
    tutoring_request = TutoringRequest.query.get(
        session.request_id)

    # Only the student can complete and rate
    if current_user.id != tutoring_request.student_id:
        flash("Only the student can rate this session.",
              "danger")
        return redirect(url_for("main.dashboard"))

    # Check if already rated
    existing_rating = Rating.query.filter_by(
        session_id=session_id).first()
    if existing_rating:
        flash("You have already rated this session.",
              "info")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        stars = int(request.form.get("stars"))
        review = request.form.get("review")

        # Create rating
        new_rating = Rating(
            stars=stars,
            review=review,
            session_id=session_id,
            student_id=current_user.id,
            tutor_id=session.tutor_id
        )
        db.session.add(new_rating)

        # Mark session as completed
        session.status = "completed"
        tutoring_request.status = "closed"
        db.session.commit()

        flash("Session completed and rated! Thank you.",
              "success")
        return redirect(url_for("main.history"))

    return render_template(
        "rate_session.html",
        session=session,
        tutoring_request=tutoring_request
    )


@main.route("/history")
@login_required
def history():
    """View session history for student or tutor."""
    if current_user.role == "student":
        past_requests = TutoringRequest.query.filter_by(
            student_id=current_user.id,
            status="closed"
        ).all()

        past_sessions = []
        for req in past_requests:
            session = Session.query.filter_by(
                request_id=req.id).first()
            rating = Rating.query.filter_by(
                session_id=session.id).first() \
                if session else None
            if session:
                past_sessions.append({
                    "request": req,
                    "session": session,
                    "rating": rating
                })

        return render_template(
            "history.html",
            past_sessions=past_sessions
        )
    else:
        my_sessions = Session.query.filter_by(
            tutor_id=current_user.id,
            status="completed"
        ).all()

        past_sessions = []
        for session in my_sessions:
            req = TutoringRequest.query.get(
                session.request_id)
            rating = Rating.query.filter_by(
                session_id=session.id).first()
            if req:
                past_sessions.append({
                    "request": req,
                    "session": session,
                    "rating": rating
                })

        return render_template(
            "history.html",
            past_sessions=past_sessions
        )


@main.route("/admin")
@login_required
def admin():
    """Admin dashboard."""
    if (current_user.email != "admin@peertutor.com" and
            current_user.role != "admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("main.dashboard"))

    total_users = User.query.filter(
        User.email != "admin@peertutor.com").count()
    total_students = User.query.filter_by(
        role="student").count()
    total_tutors = User.query.filter_by(
        role="tutor").count()
    total_requests = TutoringRequest.query.count()
    total_sessions = Session.query.count()
    total_ratings = Rating.query.count()

    all_users = User.query.filter(
        User.email != "admin@peertutor.com").all()
    all_requests = TutoringRequest.query.all()
    all_sessions = Session.query.all()

    return render_template(
        "admin.html",
        total_users=total_users,
        total_students=total_students,
        total_tutors=total_tutors,
        total_requests=total_requests,
        total_sessions=total_sessions,
        total_ratings=total_ratings,
        all_users=all_users,
        all_requests=all_requests,
        all_sessions=all_sessions
    )
@main.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Special admin login page."""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Check admin credentials
        if (email == "admin@peertutor.com" and
                password == "admin2026"):
            user = User.query.filter_by(
                email="admin@peertutor.com").first()

            # Create admin account if not exists
            if not user:
                from werkzeug.security import \
                    generate_password_hash
                user = User(
                    full_name="Admin",
                    email="admin@peertutor.com",
                    password=generate_password_hash(
                        "admin2026"),
                    role="admin"
                )
                db.session.add(user)
                db.session.commit()

            login_user(user)
            flash("Welcome Admin!", "success")
            return redirect(url_for("main.admin"))

        flash("Invalid admin credentials.", "danger")
        return redirect(url_for("main.admin_login"))

    return render_template("admin_login.html")
@main.route("/admin/delete/user/<int:user_id>")
@login_required
def delete_user(user_id):
    """Admin deletes a user."""
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("main.dashboard"))

    user = User.query.get_or_404(user_id)

    # Delete related records first
    TutoringRequest.query.filter_by(
        student_id=user_id).delete()
    Session.query.filter_by(
        tutor_id=user_id).delete()
    Rating.query.filter_by(
        student_id=user_id).delete()
    Rating.query.filter_by(
        tutor_id=user_id).delete()

    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for("main.admin"))


@main.route("/admin/delete/request/<int:request_id>")
@login_required
def delete_request(request_id):
    """Admin deletes a tutoring request."""
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("main.dashboard"))

    req = TutoringRequest.query.get_or_404(request_id)

    # Delete related sessions first
    sessions = Session.query.filter_by(
        request_id=request_id).all()
    for session in sessions:
        Message.query.filter_by(
            session_id=session.id).delete()
        Rating.query.filter_by(
            session_id=session.id).delete()
        db.session.delete(session)

    db.session.delete(req)
    db.session.commit()
    flash("Request deleted successfully.", "success")
    return redirect(url_for("main.admin"))