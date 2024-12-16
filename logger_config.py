import logging
import yaml

def setup_logger(name):
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(config['logging']['level'])
    
    # Create handlers
    file_handler = logging.FileHandler(config['logging']['file'])
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
