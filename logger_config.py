import logging
import yaml
import os

def setup_logger(name):
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(config['logging']['level'])
    
    # Ensure logs directory exists
    log_path = config['logging']['file']
    log_dir = os.path.dirname(log_path)
    
    # Create logs directory if it doesn't exist
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Create handlers
    file_handler = logging.FileHandler(log_path)
    console_handler = logging.StreamHandler()
    
    # Create formatter
    formatter = logging.Formatter(config['logging']['format'])
    
    # Set formatter for handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
