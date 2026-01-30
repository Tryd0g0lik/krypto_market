"""
__tests__/test_midllware/test_client_middleware_valid.py
"""
import logging

import pytest
from requests import Response

log = logging.getLogger(__name__)
@pytest.mark.skip
@pytest.mark.parametrize("pathname, expect", [
    ("/create", {
               "email": "example@example.com",
               "country": "US",
               "controller": {
                    "fees": {"payer": "account"},
                    "losses": {"payments": "stripe"},
                    "stripe_dashboard": {"type": "full"}
               }
           })])
async def test_enqueue_account_ofMiddleware(pathname, expect) -> None:
    """
        TODO: Для теста запустить приложение.
     - 'respons' This is a key from middleware. This key mus be to send in queue.
     - 'queue_response' This is a key from queue. This key receiving through 'StripCreationQueue.queue'.
    :param client: is the test client/fixture - 'TestClient'/
    :param request_post: response after tue post request
    :param pathname: Path name from the post resuest
    :param expect: Expect response.
    :return: None
    """
    import aiohttp
    test_response: Response | aiohttp.ClientResponse | None = None

    async with aiohttp.ClientSession(
        headers={"Content-type": "application/json"}) as session:
        async with session.post(f"http://127.0.0.1:8003/api/v1/accounts{pathname}",
                                        headers={"content-type": "application/json",
                                                 }) as response:
            test_response = response
            log_t = "[%s]: 0. 'request_post' Response => %s <= Response of test test client" % (
                test_enqueue_account_ofMiddleware.__name__,
                test_response.__dict__.__str__()
            )
            log.info(log_t)
            assert response is not None
            assert response.status != 500
            assert response.status == 200
            data_json = await response.json()
            assert isinstance(data_json, dict)

            assert data_json["detail"] is not None
            assert data_json["detail"]  == "Account in processing"
            #
            # # Create dictionary
            # # result = {k.decode(): v[0].decode() for k, v in urllib.parse.parse_qs(content).items()}
            # # result = {k.decode(): v[0].decode() for k, v in content.items()}
            # log_t = "[%s]: 2. Info => Data: %s" % (
            #     __name__,
            #     str(content),
            # )
            # log.info("2. %s Stripe_api: %s" % (log_t, QueueEnum.ACCOUNT_CREATE.value))
            #  # ----
            # respons = await controller.enqueue_account(content, test_response.headers["X-Request-ID"],
            #
            #                                            stripe_api=QueueEnum.ACCOUNT_CREATE.value)
            # log_t = "[%s]: 3. 'StripCreationQueue.enqueue_account' response! Info => %s" % (
            #     __name__,
            #     respons
            # )
            # log.info(log_t)
            # # ----

        # def test_count_get_connection()
