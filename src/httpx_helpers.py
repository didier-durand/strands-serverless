from httpx import AsyncClient, Request, Response, AsyncBaseTransport, AsyncHTTPTransport


# source: # for content: https://github.com/encode/httpx/discussions/3073

class TracingResponse(Response):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.count = 0

    async def aiter_bytes(self, *args, **kwargs):
        async for chunk in super().aiter_bytes(*args, **kwargs):
            self.count += 1
            print(f"  response chunk {self.count}: {chunk}")
            yield chunk


# usage: Client(transport=TracingTransport(httpx.AsyncHTTPTransport())
class TracingTransport(AsyncBaseTransport):

    def __init__(self, transport: AsyncBaseTransport):
        self.transport = transport

    async def handle_async_request(self, request: Request):
        response = await self.transport.handle_async_request(request)

        return TracingResponse(
            status_code=response.status_code,
            headers=response.headers,
            stream=response.stream,
            extensions=response.extensions,
        )


def create_httpx_async_client_with_hooks(**http_args) -> AsyncClient:
    async def log_request(request: Request):
        print(f"Request event hook: {request.method} - url: {request.url} - "
              f"content: {request.content} - headers: {request.headers} - Waiting for response")

    async def log_response(response: Response):
        request = response.request
        print(f"Response event hook: {request.method} {request.url} - Status: {response.status_code}")

    http_args["transport"] = TracingTransport(AsyncHTTPTransport())
    client = AsyncClient(**http_args)
    client.event_hooks['request'] = [log_request]
    client.event_hooks['response'] = [log_response]
    return client
