class algorithn_env:
    SHORT_MA: int = 5
    LONG_MA: int = 15
    RSI_PERIOD: int = 14
    MOMENTUM_DAYS: int = 5
    MOMENTUM_THRESHOLD: float = 2.0
    RSI_OVERBOUGHT: int = 70
    RSI_OVERSOLD: int = 30
    CONCENTRATION_LIMIT: float = 30.0


class database_config:
    db_name: str = "Investments"
    coll_name: str = "shares"
    maxPoolSize: int = 50
    minPoolSize: int = 5
    maxIdleTimeMS: int = 30000
    serverSelectionTimeoutMS: int = 5000
    connectTimeoutMS: int = 5000
    retryReads: bool = True
