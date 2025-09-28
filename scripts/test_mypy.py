from typing import Protocol, TypeVar, Generic, ClassVar, Type

# Define a generic Config type
C = TypeVar("C", bound="BaseConfig", covariant=True)


class BaseConfig:
    """Base class for configuration objects."""

    pass


class Agent(Protocol, Generic[C]):
    """
    Protocol for an Agent that accepts a Config class in __init__.
    """

    name: ClassVar[str]
    config_cls: ClassVar[Type[C]]

    def __init__(self, config: C) -> None:
        """
        Initialize the Agent with a configuration object.
        """
        ...

    def run(self, text: str) -> str:
        """
        Main execution method of the Agent.
        """
        ...


# Example implementation
class MyConfig(BaseConfig):
    def __init__(self, model_name: str, temperature: float = 0.7) -> None:
        self.model_name = model_name
        self.temperature = temperature


class MyAgent:
    name: ClassVar = "my_agent"
    config_cls: ClassVar = MyConfig

    def __init__(self, config: MyConfig) -> None:
        self.config = config

    def run(self, text: str) -> str:
        return f"Running {self.config.model_name} with temp={self.config.temperature} on input: {text}"


# Usage
cfg = MyConfig(model_name="gpt-neo", temperature=0.9)
# agent: Agent[MyConfig] = MyAgent(cfg)
agent: Agent[BaseConfig] = MyAgent(cfg)
print(agent.run("Hello!"))

agent_cls: type[Agent] = MyAgent
# agent_cls: type[Agent[MyConfig]] = MyAgent
