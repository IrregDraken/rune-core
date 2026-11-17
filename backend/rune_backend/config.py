from __future__ import annotations
from functools import lru_cache
from pydantic import Field,field_validator
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_prefix="RUNE_",env_file=".env",env_file_encoding="utf-8",extra="ignore")
    backend_env:str="development"
    backend_host:str="127.0.0.1"
    backend_port:int=Field(default=8787,ge=1,le=65535)
    backend_allowed_origins:list[str]=Field(default_factory=lambda:["http://localhost:3000","http://127.0.0.1:3000"])
    supabase_url:str|None=None
    supabase_publishable_key:str|None=None
    supabase_secret_key:str|None=None
    @field_validator("backend_allowed_origins",mode="before")
    @classmethod
    def parse_origins(cls,value:object)->object:
        if isinstance(value,str): return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value
    @field_validator("backend_allowed_origins")
    @classmethod
    def reject_wildcard_origins(cls,value:list[str])->list[str]:
        if "*" in value: raise ValueError("Wildcard CORS origins are forbidden")
        return value

@lru_cache
def get_settings()->Settings:
    return Settings()
