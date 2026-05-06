#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Enterprise Entry Point
Production-grade auto customer acquisition system
"""

import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from acas_pro.core.config import config
from acas_pro.core.logging import setup_logging, get_logger
from acas_pro.core.database import db
from acas_pro.ui.main_window import MainWindow

logger = get_logger(__name__)


def main():
    """Application entry point"""
    # Setup logging
    setup_logging()
    logger.info("=" * 50)
    logger.info(f"{config.name} v{config.version} starting...")
    logger.info("=" * 50)
    
    # Initialize database
    try:
        _ = db  # Trigger initialization
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(config.name)
    app.setApplicationVersion(config.version)
    app.setOrganizationName(config.company)
    
    # Set application font
    font = QFont(config.ui.font_family, config.ui.font_size)
    app.setFont(font)
    
    # Enable high DPI support
    app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    logger.info("Application started successfully")
    
    # Run event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
