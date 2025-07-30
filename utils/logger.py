import logging
from pathlib import Path
from datetime import datetime

def setup_logging():
    """Configura o sistema de logs"""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"lincon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logger = logging.getLogger('lincon')
    logger.setLevel(logging.INFO)
    logger.propagate = False  # <-- Impede logs no console

    # Remove handlers antigos para evitar duplicidade
    if logger.hasHandlers():
        logger.handlers.clear()

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    return logger
