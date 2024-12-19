from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True)
    total_messages = Column(Integer, default=0)
    streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    last_active_date = Column(DateTime)
    night_owl_messages = Column(Integer, default=0)
    early_bird_messages = Column(Integer, default=0)
    weekend_messages = Column(Integer, default=0)
    weekday_messages = Column(Integer, default=0)
    
    # Relationships
    messages = relationship("Message", back_populates="user")
    activity_patterns = relationship("ActivityPattern", back_populates="user")
    badges = relationship("UserBadge", back_populates="user")

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    discord_message_id = Column(String, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    channel_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    reaction_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="messages")

class ActivityPattern(Base):
    __tablename__ = 'activity_patterns'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    hour = Column(Integer)  # 0-23
    day_of_week = Column(Integer)  # 0-6
    message_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="activity_patterns")

class Badge(Base):
    __tablename__ = 'badges'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(String)
    emoji = Column(String)
    requirement_type = Column(String)  # percentage, count, streak
    requirement_value = Column(Float)

class UserBadge(Base):
    __tablename__ = 'user_badges'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    badge_id = Column(Integer, ForeignKey('badges.id'))
    earned_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="badges")
    badge = relationship("Badge")

# Create all tables
Base.metadata.create_all(engine)

# Initialize default badges
def init_default_badges():
    session = Session()
    default_badges = [
        {
            'name': 'Night Owl',
            'description': '30% of messages during night hours (10 PM - 4 AM)',
            'emoji': '🦉',
            'requirement_type': 'percentage',
            'requirement_value': 30.0
        },
        {
            'name': 'Early Bird',
            'description': '30% of messages during early hours (5 AM - 9 AM)',
            'emoji': '🌅',
            'requirement_type': 'percentage',
            'requirement_value': 30.0
        },
        {
            'name': 'Weekend Warrior',
            'description': '40% of messages during weekends',
            'emoji': '🎮',
            'requirement_type': 'percentage',
            'requirement_value': 40.0
        },
        {
            'name': 'Consistent Contributor',
            'description': 'Maintained a 7-day streak',
            'emoji': '🔥',
            'requirement_type': 'streak',
            'requirement_value': 7.0
        }
    ]
    
    for badge_data in default_badges:
        if not session.query(Badge).filter_by(name=badge_data['name']).first():
            badge = Badge(**badge_data)
            session.add(badge)
    
    session.commit()
    session.close()

# Initialize badges
init_default_badges() 