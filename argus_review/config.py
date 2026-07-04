from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    YamlConfigSettingsSource,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource
)

from argus_review.libs.config.agent import AgentConfig
from argus_review.libs.config.artifacts import ArtifactsConfig
from argus_review.libs.config.conventions import ConventionsConfig
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

        # GitHub Actions sets an env var to an empty string when the
        # corresponding secret/input is unset, rather than leaving it
        # undefined. Without this, an unset optional override (e.g.
        # LLM__PROVIDER left empty on purpose) would be treated as an
        # explicit empty value and fail validation instead of falling
        # back to the YAML/JSON config.
        env_ignore_empty=True,

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
    conventions: ConventionsConfig = ConventionsConfig()
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
        # pydantic-settings uses "first source wins" for any given field, so
        # sources listed first here have the *highest* priority.
        #
        # Order (highest -> lowest priority):
        #   1. init args        - explicit constructor kwargs (mainly for tests)
        #   2. environment vars - e.g. LLM__PROVIDER, LLM__META__MODEL, secrets in CI
        #   3. .env file
        #   4. YAML file        - project defaults / baseline config
        #   5. JSON file
        #
        # This lets CI/CD override provider/model/tokens via env vars or repo
        # secrets (e.g. LLM__PROVIDER=CLAUDE, LLM__META__MODEL=gpt-4o) without
        # having to edit the committed YAML config.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(cls),
            JsonConfigSettingsSource(cls),
        )


settings = Settings()
