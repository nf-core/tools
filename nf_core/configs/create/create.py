"""Creates a nextflow config matching the current
nf-core organization specification.
"""

from pathlib import Path
from re import sub
from nf_core.configs.create.serial import NextflowSerial
from nf_core.configs.create.utils import ConfigsCreateConfig


class ConfigCreate:

    def __init__(self, template_config: ConfigsCreateConfig, config_type: str, config_dir: Path | str = Path(".")):
        self.template_config = template_config
        self.config_type = config_type
        config_dir_path = config_dir if isinstance(config_dir, Path) else Path(config_dir)
        assert not config_dir_path.is_file(), f'Error: the path "{str(config_dir_path)}" is a file.'
        # Create directory if it doesn't already exist
        config_dir_path.mkdir(parents=True, exist_ok=True)
        self.config_dir = config_dir_path

    def write_to_file(self):
        ## File name option
        config_name = str(self.template_config.general_config_name).strip()
        config_name_clean = sub(r"\W+" "_", config_name)
        config_name_clean = sub(r"_+$", "", config_name_clean)
        filename = f"{config_name_clean}.conf"
        filename = self.config_dir / filename

        if not (
            self.config_type == "pipeline" or
            self.config_type == "infrastructure"
        ):
            raise ValueError(f"Invalid config type: {self.config_type}")

        serial_data = NextflowSerial.dumps(self.template_config.serial(), drop_null=True)

        with open(filename, "w+") as file:
            ## Write params
            file.write(serial_data)
