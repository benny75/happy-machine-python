from .zacks_scraper import get_weekly_earnings_from_zacks, save_weekly_earnings_to_csv

try:
    from .zacks_selenium_scraper import get_weekly_earnings_selenium, save_weekly_earnings_selenium_to_csv
    __all__ = ['get_weekly_earnings_from_zacks', 'save_weekly_earnings_to_csv', 
               'get_weekly_earnings_selenium', 'save_weekly_earnings_selenium_to_csv']
except ImportError:
    # Selenium not available
    __all__ = ['get_weekly_earnings_from_zacks', 'save_weekly_earnings_to_csv']