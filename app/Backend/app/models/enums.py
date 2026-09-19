import enum


class UserRole(str, enum.Enum):
    SUPPORT_AGENT = "SUPPORT_AGENT"
    SUPPORT_MANAGER = "SUPPORT_MANAGER"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    ADMIN = "ADMIN"


class ConversationChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    CHAT = "CHAT"
    TICKET = "TICKET"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    OTHER = "OTHER"


class ConversationStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class CampaignStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    MONITORED = "MONITORED"
    RESOLVED = "RESOLVED"


class SenderType(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"


class Sentiment(str, enum.Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class Priority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ComplaintCategory(str, enum.Enum):
    ACCOUNT_ACCESS = "ACCOUNT_ACCESS"
    PAYMENT_BILLING = "PAYMENT_BILLING"
    TECHNICAL_ISSUE = "TECHNICAL_ISSUE"
    SERVICE_REQUEST = "SERVICE_REQUEST"
    OTHER = "OTHER"


class ResolutionStatus(str, enum.Enum):
    UNRESOLVED = "UNRESOLVED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
