"""
cryptomarket/type/deribit_type.py
"""

from pydantic import BaseModel, Field


class OAuthAutenticationParamsType(BaseModel):

    grant_type: str = Field(default="client_credentials")
    client_id: str = Field(default="YOUR_CLIENT_ID")
    client_secret: str = Field(default="YOUR_CLIENT_SECRET")


class OAuthAutenticationType(BaseModel):
    """
    Method used to authenticate
    https://docs.deribit.com/articles/deribit-quickstart#websocket-authentication
    Template for a user authentication:
        '''
        {
            "jsonrpc": "2.0",
            "method": "public/auth",
            "params": {
              "grant_type": "client_credentials",
              "client_id": "YOUR_CLIENT_ID",
              "client_secret": "YOUR_CLIENT_SECRET"
            },
            "id": 1
          }

        '''
    return
    """

    id: int = Field(gt=0, description="Must be a positive integer")
    api_key: str = Field(description="""Must be a string contain the api key (url)""")
    jsonrpc: str = Field(
        pattern="^\d+\.\d+$", default="2.0", description="JSON-RPC version"
    )
    method: str = Field(
        pattern="^(public\/auth)$",
        default="public/auth",
        description="Method used to the authentication",
    )
    params: dict = OAuthAutenticationParamsType

    class Config:
        from_attributes = True
