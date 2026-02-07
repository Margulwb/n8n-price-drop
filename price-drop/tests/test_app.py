import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['TELEGRAM_CHAT_ID'] = 'test_chat_id'
os.environ['TELEGRAM_TOKEN'] = 'test_token'
os.environ['CHECK_INTERVAL'] = '300'


with patch('apscheduler.schedulers.background.BackgroundScheduler.start'), \
     patch('apscheduler.schedulers.background.BackgroundScheduler.add_job'), \
     patch('apscheduler.schedulers.background.BackgroundScheduler.shutdown'):
    from app import app
    from src.config import SYMBOL_NAMES, SYMBOLS, ALERT_THRESHOLD_FIRST, ALERT_THRESHOLD_STEP
    from src.price_checker import get_next_threshold, check_prices
    import src.price_checker as price_checker_module


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_returns_healthy(self, client):
        data = json.loads(response.data) if (response := client.get('/health')) else {}
        assert data['status'] == 'healthy'
        assert data['service'] == 'price-drop-tracker'


class TestIndexEndpoint:
    def test_index_returns_200(self, client):
        response = client.get('/')
        assert response.status_code == 200

    def test_index_returns_html(self, client):
        response = client.get('/')
        assert b'Price Drop Tracker' in response.data


class TestStatusEndpoint:
    def test_status_no_checks(self, client):
        price_checker_module.last_check_status = None
        response = client.get('/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'no_checks_yet'

    def test_status_with_data(self, client):
        price_checker_module.last_check_status = {
            'timestamp': '2026-02-07T12:00:00',
            'results': [{'symbol': 'ISAC.L', 'status': 'checked'}],
            'success': True
        }
        response = client.get('/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestSymbolsEndpoint:
    def test_symbols_returns_200(self, client):
        response = client.get('/symbols')
        assert response.status_code == 200

    def test_symbols_returns_all(self, client):
        response = client.get('/symbols')
        data = json.loads(response.data)
        assert data['count'] == len(SYMBOLS)
        assert 'ETFBW20TR.WA' in data['symbols']


class TestCheckPricesEndpoint:
    @patch('src.routes.check_prices')
    def test_check_prices_endpoint(self, mock_check, client):
        response = client.post('/check-prices')
        assert response.status_code == 200
        mock_check.assert_called_once()


class TestSendStatusTelegramEndpoint:
    def test_no_data_yet(self, client):
        price_checker_module.last_check_status = None
        response = client.post('/send-status-telegram')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status_sent'] is False

    @patch('src.routes.send_telegram')
    def test_sends_status(self, mock_telegram, client):
        price_checker_module.last_check_status = {
            'timestamp': '2026-02-07T12:00:00',
            'results': [
                {'symbol': 'ISAC.L', 'name': 'MSCI ACWI Globalny', 'price': 111.75, 'change_pct': 0.05, 'status': 'checked', 'alert_sent': False}
            ],
            'success': True
        }
        response = client.post('/send-status-telegram')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status_sent'] is True
        mock_telegram.assert_called_once()


class TestGetNextThreshold:
    def test_threshold_at_minus_1(self):
        assert get_next_threshold(-1.0) == -1.0

    def test_threshold_at_minus_1_3(self):
        assert get_next_threshold(-1.3) == -1.0

    def test_threshold_at_minus_1_5(self):
        assert get_next_threshold(-1.5) == -1.5

    def test_threshold_at_minus_1_7(self):
        assert get_next_threshold(-1.7) == -1.5

    def test_threshold_at_minus_2_1(self):
        assert get_next_threshold(-2.1) == -2.0

    def test_threshold_at_minus_3_0(self):
        assert get_next_threshold(-3.0) == -3.0

    def test_threshold_at_minus_5_4(self):
        assert get_next_threshold(-5.4) == -5.0


class TestMarketHours:
    @patch('src.price_checker.log_to_file')
    def test_skips_before_9(self, mock_log):
        with patch('src.price_checker.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 7, 8, 30, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            check_prices()
            mock_log.assert_called_with("Market closed (08:30:00). Skipping check.")

    @patch('src.price_checker.log_to_file')
    def test_skips_after_18(self, mock_log):
        with patch('src.price_checker.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 7, 18, 0, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            check_prices()
            mock_log.assert_called_with("Market closed (18:00:00). Skipping check.")


class TestSymbolNames:
    def test_all_symbols_have_names(self):
        for symbol in SYMBOLS:
            assert symbol in SYMBOL_NAMES

    def test_wig20_mapping(self):
        assert SYMBOL_NAMES['ETFBW20TR.WA'] == 'WIG20'

    def test_sp500_mapping(self):
        assert SYMBOL_NAMES['CSPX.L'] == 'S&P 500'

    def test_nasdaq_mapping(self):
        assert SYMBOL_NAMES['CNDX.L'] == 'NASDAQ 100'

    def test_semiconductor_mapping(self):
        assert SYMBOL_NAMES['VVSM.DE'] == 'Semiconductor'


class TestConfig:
    def test_alert_threshold_first(self):
        assert ALERT_THRESHOLD_FIRST == -1.0

    def test_alert_threshold_step(self):
        assert ALERT_THRESHOLD_STEP == -0.5

    def test_symbols_count(self):
        assert len(SYMBOLS) == 8


class TestAlertThresholds:
    def test_save_and_get_thresholds(self, tmp_path):
        memory_file = str(tmp_path / "alert_thresholds")
        with patch('src.config.ALERT_THRESHOLDS_FILE', memory_file), \
             patch('src.alerts.ALERT_THRESHOLDS_FILE', memory_file):
            from src.alerts import save_alert_threshold, get_alert_thresholds
            save_alert_threshold('ISAC.L', -1.0)
            thresholds = get_alert_thresholds()
            assert thresholds['ISAC.L'] == -1.0

    def test_get_thresholds_empty(self, tmp_path):
        memory_file = str(tmp_path / "nonexistent")
        with patch('src.config.ALERT_THRESHOLDS_FILE', memory_file), \
             patch('src.alerts.ALERT_THRESHOLDS_FILE', memory_file):
            from src.alerts import get_alert_thresholds
            assert get_alert_thresholds() == {}

    def test_cleanup_old_date(self, tmp_path):
        memory_file = str(tmp_path / "alert_thresholds")
        with open(memory_file, 'w') as f:
            json.dump({'date': '2020-01-01', 'thresholds': {'ISAC.L': -1.0}}, f)
        with patch('src.config.ALERT_THRESHOLDS_FILE', memory_file), \
             patch('src.alerts.ALERT_THRESHOLDS_FILE', memory_file):
            from src.alerts import cleanup_alert_file
            cleanup_alert_file()
            assert not os.path.exists(memory_file)


class TestLogs:
    def test_log_to_file(self, tmp_path):
        log_dir = str(tmp_path)
        with patch('src.config.LOG_DIR', log_dir), \
             patch('src.logs.LOG_DIR', log_dir):
            from src.logs import log_to_file
            log_to_file("test message")
            today = datetime.now().strftime('%Y-%m-%d')
            log_path = os.path.join(log_dir, f"{today}.log")
            assert os.path.exists(log_path)
            with open(log_path) as f:
                content = f.read()
            assert "test message" in content

    def test_cleanup_old_logs(self, tmp_path):
        log_dir = str(tmp_path)
        old_log = os.path.join(log_dir, "2020-01-01.log")
        with open(old_log, 'w') as f:
            f.write("old log")
        with patch('src.config.LOG_DIR', log_dir), \
             patch('src.logs.LOG_DIR', log_dir):
            from src.logs import cleanup_old_logs
            cleanup_old_logs()
            assert not os.path.exists(old_log)
