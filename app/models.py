from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    """Represents a student or tutor in the system."""
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True,
                      nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime,
                           default=datetime.utcnow)

    requests = db.relationship(
        "TutoringRequest",
        foreign_keys="TutoringRequest.student_id",
        backref="student",
        lazy=True
    )
    sessions = db.relationship(
        "Session",
        foreign_keys="Session.tutor_id",
        backref="tutor",
        lazy=True
    )

    def __repr__(self):
        return f"<User {self.full_name} - {self.role}>"


class TutoringRequest(db.Model):
    """Represents a tutoring request made by a student."""
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="open")
    created_at = db.Column(db.DateTime,
                           default=datetime.utcnow)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    def __repr__(self):
        return f"<Request {self.subject} - {self.status}>"


class Session(db.Model):
    """Represents a booked tutoring session."""
    id = db.Column(db.Integer, primary_key=True)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="upcoming")
    request_id = db.Column(
        db.Integer,
        db.ForeignKey("tutoring_request.id"),
        nullable=False
    )
    tutor_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
    created_at = db.Column(db.DateTime,
                           default=datetime.utcnow)
    messages = db.relationship(
        "Message",
        backref="session",
        lazy=True
    )

    def __repr__(self):
        return f"<Session {self.id} - {self.status}>"


class Message(db.Model):
    """Represents a chat message between student
    and tutor."""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime,
                          default=datetime.utcnow)
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("session.id"),
        nullable=False
    )
    sender = db.relationship(
        "User", foreign_keys=[sender_id])

    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id}>"


class Rating(db.Model):
    """Represents a rating given by a student to a tutor."""
    id = db.Column(db.Integer, primary_key=True)
    stars = db.Column(db.Integer, nullable=False)
    review = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime,
                           default=datetime.utcnow)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("session.id"),
        nullable=False
    )
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
    tutor_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
    student = db.relationship(
        "User", foreign_keys=[student_id])
    tutor = db.relationship(
        "User", foreign_keys=[tutor_id])

    def __repr__(self):
        return f"<Rating {self.stars} stars>"