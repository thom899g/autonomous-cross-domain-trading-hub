"""
Configuration management for the trading hub.
Centralizes all environment variables and configuration with validation.
"""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MarketType(Enum):
    """Supported market types for extensibility"""
    CRYPTO = "crypto"
    EQUITIES = "equities"
    FOREX = "forex"
    FUTURES = "futures"

class RiskTolerance(Enum):
    """Risk management profiles"""
    CONSERVATIVE = 0.25
    MODERATE = 0.5
    AGGRESSIVE = 0.75

@dataclass
class ExchangeConfig:
    """Configuration for individual exchanges"""
    name: str
    api_key: str = ""
    api_secret: str = ""
    sandbox: bool = True
    rate_limit: int = 1000  # requests per minute
    enabled: bool = False
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.name:
            raise ValueError("Exchange name cannot be empty")
        
        # For production, require API credentials
        if not self.sandbox and not (self.api_key and self.api_secret):
            logging.warning(f"Exchange {self.name}: Missing API credentials for production mode")

@dataclass
class TradingConfig:
    """Global trading configuration"""
    # Risk Management
    max_position_size: float = 0.1  # 10% of portfolio per trade
    daily_loss_limit: float = 0.02  # 2% max daily loss
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    
    # Execution
    slippage_tolerance: float = 0.005  # 0.5% max slippage
    minimum_volume: float = 10000.0  # Minimum daily volume for trading
    
    # Monitoring
    heartbeat_interval: int = 60  # seconds
    market_data_refresh: int = 30  # seconds

class Settings:
    """Singleton configuration manager"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize all configuration from environment"""
        # Firebase Configuration
        self.firebase_credentials = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
        self.firebase_database = os.getenv("FIREBASE_DATABASE_URL", "")
        
        # Telegram Alerts
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        # Initialize exchanges
        self.exchanges = self._load_exchange_configs()
        
        # Trading Configuration
        self.trading = TradingConfig()
        
        # Strategy Parameters
        self.enabled_markets = self._parse_markets(os.getenv("ENABLED_MARKETS", "CRYPTO"))
        
        # Logging Level
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        self._validate_configuration()
    
    def _load_exchange_configs(self) -> Dict[str, ExchangeConfig]:
        """Load exchange configurations from environment"""
        exchanges = {}
        
        # Crypto Exchanges
        exchange_names = ["binance", "coinbase", "kraken", "bybit"]
        
        for name in exchange_names:
            api_key = os.getenv(f"{name.upper()}_API_KEY", "")
            api_secret = os.getenv(f"{name.upper()}_API_SECRET", "")
            sandbox = os.getenv(f"{name.upper()}_SANDBOX", "true").lower() == "true"
            enabled = os.getenv(f"{name.upper()}_ENABLED", "false").lower() == "true"
            
            exchanges[name] = ExchangeConfig(
                name=name,
                api_key=api_key,
                api_secret=api_secret,
                sandbox=sandbox,
                enabled=enabled
            )
        
        return exchanges
    
    def _parse_markets(self, markets_str: str) -> List[MarketType]:
        """Parse enabled markets from string"""
        markets = []
        for market in markets_str.split(","):
            try:
                markets.append(MarketType[market.strip().upper()])
            except KeyError:
                logging.warning(f"Unknown market type: {market}")
        return markets
    
    def _validate_configuration(self):
        """Validate critical configuration"""
        errors = []
        
        # Check Firebase
        if not self.firebase_credentials:
            errors.append("FIREBASE_CREDENTIALS_PATH not set")
        
        # Check at least one exchange is enabled
        enabled_exchanges = [e for e in self.exchanges.values() if e.enabled]
        if not enabled_exchanges:
            errors.append("No exchanges enabled. Set at least one exchange to enabled=true")
        
        # Check for API credentials if not in sandbox
        for exchange in enabled_exchanges:
            if not exchange