from flask import (Blueprint, render_template, redirect,
                   url_for, request, flash)
from flask_login import (login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import (generate_password_hash,
                                check_password_hash)
from app import db
from app.models import User, TutoringRequest, Session, Message

# Create Blueprint
main = Blueprint("main", __name__)


@main.route("/")
def home():
    """Home page."""
    return render_template("home.html")


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