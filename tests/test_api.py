from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import SolarkCloudClient


class ParserTests(unittest.TestCase):
    def test_positive_grid_power_is_import(self) -> None:
        metrics = SolarkCloudClient.parse_metrics_from_flow(
            {
                "pvPower": 4200,
                "loadOrEpsPower": 3100,
                "gridOrMeterPower": 900,
                "battPower": -200,
                "soc": 75,
            }
        )
        self.assertEqual(metrics["grid_import_power"], 900.0)
        self.assertEqual(metrics["grid_export_power"], 0.0)

    def test_negative_grid_power_is_export(self) -> None:
        metrics = SolarkCloudClient.parse_metrics_from_flow(
            {"gridOrMeterPower": -750}
        )
        self.assertEqual(metrics["grid_import_power"], 0.0)
        self.assertEqual(metrics["grid_export_power"], 750.0)

    def test_invert_grid_sign_is_applied(self) -> None:
        metrics = SolarkCloudClient.parse_metrics_from_flow(
            {"gridOrMeterPower": 750}, invert=True
        )
        self.assertEqual(metrics["grid_import_power"], 0.0)
        self.assertEqual(metrics["grid_export_power"], 750.0)

    def test_missing_grid_power_is_safe(self) -> None:
        metrics = SolarkCloudClient.parse_metrics_from_flow({"pvPower": 1000})
        self.assertIsNone(metrics["grid_import_power"])
        self.assertIsNone(metrics["grid_export_power"])

    def test_nested_flow_and_malformed_numbers_are_safe(self) -> None:
        metrics = SolarkCloudClient.parse_metrics_from_flow(
            {"flow": {"pvPower": "1234.5", "gridOrMeterPower": "not-a-number"}}
        )
        self.assertEqual(metrics["pv_power"], 1234.5)
        self.assertIsNone(metrics["grid_import_power"])
        self.assertIsNone(metrics["grid_export_power"])

    def test_cloud_daily_energy_fields_are_not_estimated(self) -> None:
        metrics = SolarkCloudClient.parse_grid_energy_today_from_generation_use(
            {
                "gridBuy": "3.2",
                "gridSell": 1.1,
                "load": "8.4",
                "batteryCharge": None,
            }
        )
        self.assertEqual(metrics["grid_import_energy_today"], 3.2)
        self.assertEqual(metrics["grid_export_energy_today"], 1.1)
        self.assertEqual(metrics["load_energy_today"], 8.4)
        self.assertIsNone(metrics["battery_charge_energy_today"])
        self.assertIsNone(metrics["battery_discharge_energy_today"])

    def test_pv_energy_today_is_cloud_value(self) -> None:
        self.assertEqual(
            SolarkCloudClient.parse_energy_today_from_generation_use(
                {"pv": "12.75"}
            ),
            12.75,
        )
        self.assertIsNone(
            SolarkCloudClient.parse_energy_today_from_generation_use({})
        )


class _FakeResponse:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def json(self, content_type=None):
        return self._payload


class _FakeSession:
    def __init__(self, *, posts=None, gets=None) -> None:
        self.posts = list(posts or [])
        self.gets = list(gets or [])
        self.post_calls = []
        self.get_calls = []

    def post(self, url, *, json, headers):
        self.post_calls.append((url, json, headers))
        return self.posts.pop(0)

    def get(self, url, *, headers, params):
        self.get_calls.append((url, headers, params))
        return self.gets.pop(0)


class ClientBoundTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_fallback_is_bounded_and_uses_portal_origin(self) -> None:
        session = _FakeSession(
            posts=[
                _FakeResponse(401, {}),
                _FakeResponse(401, {}),
                _FakeResponse(200, {"access_token": "ok", "expires_in": 3600}),
            ]
        )
        client = SolarkCloudClient(
            "user",
            "secret",
            "12345",
            session,
            api_url="https://p2.api.solarkcloud.com",
            origin_url="https://www.solarkcloud.com",
            fallback_urls=("https://api.solarkcloud.com",),
            auth_mode="auto",
        )

        await client._login()

        self.assertEqual(len(session.post_calls), 3)
        self.assertEqual(client._api_url, "https://api.solarkcloud.com")
        self.assertEqual(
            session.post_calls[0][2].get("Origin"), "https://www.solarkcloud.com"
        )
        self.assertNotIn("Origin", session.post_calls[1][2])
        self.assertEqual(
            session.post_calls[2][2].get("Origin"), "https://www.solarkcloud.com"
        )

    async def test_401_get_reauthenticates_once_then_succeeds(self) -> None:
        session = _FakeSession(
            posts=[_FakeResponse(200, {"access_token": "new", "expires_in": 3600})],
            gets=[
                _FakeResponse(401, {}),
                _FakeResponse(200, {"data": {"pvPower": 1000}}),
            ],
        )
        client = SolarkCloudClient(
            "user",
            "secret",
            "12345",
            session,
            api_url="https://p2.api.solarkcloud.com",
            origin_url="https://www.solarkcloud.com",
            auth_mode="strict",
        )
        client._token = "expired"
        client._token_expiry = 10**12

        payload = await client._request_json("/test")

        self.assertEqual(payload["data"]["pvPower"], 1000)
        self.assertEqual(len(session.get_calls), 2)
        self.assertEqual(len(session.post_calls), 1)

    async def test_bad_credentials_stop_after_four_auto_attempts(self) -> None:
        from api import SolarkAuthError

        session = _FakeSession(posts=[_FakeResponse(401, {}) for _ in range(4)])
        client = SolarkCloudClient(
            "user",
            "wrong",
            "12345",
            session,
            api_url="https://p2.api.solarkcloud.com",
            origin_url="https://www.solarkcloud.com",
            fallback_urls=("https://api.solarkcloud.com",),
            auth_mode="auto",
        )

        with self.assertRaises(SolarkAuthError):
            await client._login()

        self.assertEqual(len(session.post_calls), 4)

if __name__ == "__main__":
    unittest.main()
