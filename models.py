from datetime import datetime
from app import db
from sqlalchemy import Enum, func
import enum

class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"

class University(enum.Enum):
    ADDIS_ABABA_UNIVERSITY = "Addis Ababa University"
    BAHIR_DAR_UNIVERSITY = "Bahir Dar University"
    HAWASSA_UNIVERSITY = "Hawassa University"
    JIMMA_UNIVERSITY = "Jimma University"
    MEKELLE_UNIVERSITY = "Mekelle University"
    GONDAR_UNIVERSITY = "Gondar University"
    ADAMA_SCIENCE_AND_TECHNOLOGY_UNIVERSITY = "Adama Science and Technology University"
    HARAMAYA_UNIVERSITY = "Haramaya University"
    ARBA_MINCH_UNIVERSITY = "Arba Minch University"
    DIRE_DAWA_UNIVERSITY = "Dire Dawa University"
    ALL_UNIVERSITIES = "All Universities"

class User(db.Model):
    """User table for storing user profiles"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(Enum(Gender), nullable=False)
    interested_in = db.Column(Enum(Gender), nullable=False)
    university = db.Column(Enum(University), nullable=False)
    bio = db.Column(db.String(500), nullable=True)
    photo_id = db.Column(db.String(100), nullable=True)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_banned = db.Column(db.Boolean, default=False)
    registration_complete = db.Column(db.Boolean, default=False)
    current_state = db.Column(db.String(50), nullable=True)

    # Relationships
    likes_sent = db.relationship('Like', foreign_keys='Like.user_id', backref='sender', lazy='dynamic')
    likes_received = db.relationship('Like', foreign_keys='Like.liked_user_id', backref='receiver', lazy='dynamic')
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    messages_received = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')
    reports_filed = db.relationship('Report', foreign_keys='Report.reporter_id', backref='reporter', lazy='dynamic')
    reports_received = db.relationship('Report', foreign_keys='Report.reported_user_id', backref='reported', lazy='dynamic')
    confessions = db.relationship('Confession', backref='user', lazy='dynamic')

    def __repr__(self):
        return f"<User {self.telegram_id} - {self.full_name}>"

class Like(db.Model):
    """Like table for storing user likes/dislikes"""
    __tablename__ = 'likes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    liked_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_like = db.Column(db.Boolean, default=True)  # True for like, False for dislike
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'liked_user_id', name='_user_liked_user_uc'),
    )

    def __repr__(self):
        return f"<Like {self.user_id} -> {self.liked_user_id} ({self.is_like})>"

class Match(db.Model):
    """Match table for storing matched users"""
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    
    user1 = db.relationship('User', foreign_keys=[user1_id])
    user2 = db.relationship('User', foreign_keys=[user2_id])

    __table_args__ = (
        db.UniqueConstraint('user1_id', 'user2_id', name='_user1_user2_uc'),
    )

    def __repr__(self):
        return f"<Match {self.user1_id} <-> {self.user2_id}>"

class Message(db.Model):
    """Message table for storing messages between matched users"""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    match = db.relationship('Match')

    def __repr__(self):
        return f"<Message {self.sender_id} -> {self.receiver_id}>"

class Report(db.Model):
    """Report table for storing user reports"""
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_resolved = db.Column(db.Boolean, default=False)
    resolution_notes = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Report {self.reporter_id} reported {self.reported_user_id}>"

class Confession(db.Model):
    """Confession table for storing anonymous confessions"""
    __tablename__ = 'confessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=False)
    is_posted = db.Column(db.Boolean, default=False)
    channel_message_id = db.Column(db.BigInteger, nullable=True)

    def __repr__(self):
        return f"<Confession {self.id} by {self.user_id}>"

class Admin(db.Model):
    """Admin table for storing bot administrators"""
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Admin {self.telegram_id} - {self.full_name}>"

class BannedWord(db.Model):
    """BannedWord table for storing offensive words to filter in confessions"""
    __tablename__ = 'banned_words'

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BannedWord {self.word}>"

class UserState(db.Model):
    """UserState table for storing user conversation states"""
    __tablename__ = 'user_states'

    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    state = db.Column(db.String(100), nullable=False)
    data = db.Column(db.JSON, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserState {self.telegram_id} - {self.state}>"
