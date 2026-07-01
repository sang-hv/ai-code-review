from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    YamlConfigSettingsSource,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource
)

from argus_review.libs.config.agent import AgentConfig
from argus_review.libs.config.artifacts import ArtifactsConfig
from argus_review.libs.config.base import (
    get_env_config_file_or_default,
    get_yaml_config_file_or_default,
    get_json_config_file_or_default
)
from argus_review.libs.config.core import CoreConfig
from argus_review.libs.config.llm.base import LLMConfig
from argus_review.libs.config.logger import LoggerConfig
from argus_review.libs.config.prompt import PromptConfig
from argus_review.libs.config.review import ReviewConfig
from argus_review.libs.config.vcs.base import VCSConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='allow',

        env_file=get_env_config_file_or_default(),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",

        yaml_file=get_yaml_config_file_or_default(),
        yaml_file_encoding="utf-8",

        json_file=get_json_config_file_or_default(),
        json_file_encoding="utf-8"
    )

    llm: LLMConfig
    vcs: VCSConfig
    core: CoreConfig = CoreConfig()
    agent: AgentConfig = AgentConfig()
    prompt: PromptConfig = PromptConfig()
    review: ReviewConfig = ReviewConfig()
    logger: LoggerConfig = LoggerConfig()
    artifacts: ArtifactsConfig = ArtifactsConfig()

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            YamlConfigSettingsSource(cls),
            JsonConfigSettingsSource(cls),
            env_settings,
            dotenv_settings,
            init_settings,
        )


settings = Settings()
