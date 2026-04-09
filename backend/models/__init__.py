# Import all models so SQLAlchemy metadata is populated
from models.agent import Agent
from models.message import AgentMessage
from models.portfolio import PortfolioSnapshot, SystemConfig
from models.token import DashboardToken
from models.trade import Trade

__all__ = ["Agent", "AgentMessage", "PortfolioSnapshot", "SystemConfig", "DashboardToken", "Trade"]
