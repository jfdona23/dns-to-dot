"""
Information about the DNS-over-TLS provider to be used.
"""
# from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module

# dot_providers_dict = {
#     "cloudfare": [
#         {"ip": "1.1.1.1", "port": 853},
#         {"ip": "1.0.0.1", "port": 853},
#     ],
#     "google": [
#         {"ip": "8.8.8.8", "port": 853},
#         {"ip": "8.8.4.4", "port": 853},
#     ],
# }

# class DotProviders(BaseModel):
#     """ DotProviders """

#     cloudfare: list = Field()
#     google: list = Field()

# class DotProvidersData(BaseModel):
#     """ DotProvidersData """

#     ip: str = Field()
#     port: int = Field()

# providers = DotProviders(**dot_providers_dict)

providers = {
    "cloudfare1": {"ip": "1.1.1.1", "port": 853},
    "cloudfare2": {"ip": "1.0.0.1", "port": 853},
    "google1": {"ip": "8.8.8.8", "port": 853},
    "google2": {"ip": "8.8.4.4", "port": 853},
}
