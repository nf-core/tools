from typing import Any


class NextflowSerial:
    def __init__(self, data_dict: dict | None, tab_indent: int | None = 4):
        self.data_dict = data_dict

    def __getitem__(self, key: Any | None) -> Any:
        """Returns value from data"""
        if not isinstance(self.data_dict, dict):
            raise ValueError("NextflowSerial object is not initialised, cannot index.")
        return self.data_dict[key]

    def __setitem__(self, key: Any | None, value: Any | None) -> None:
        """Sets value in data"""
        if not isinstance(self.data_dict, dict):
            raise ValueError("NextflowSerial object is not initialised, cannot index.")
        self.data_dict[key] = value

    @staticmethod
    def _stringify(data: Any | None, quote: bool = True) -> str:
        """Return nextflow compatible value"""
        quote_char = "'" if quote else ""
        if isinstance(data, str):
            return f"{quote_char}{data}{quote_char}"
        if isinstance(data, bool):
            return "true" if data else "false"
        if isinstance(data, type(None)):
            return "null"
        return str(data)  # Fallback on the Python str function if no matches

    @staticmethod
    def dumps(
        data_dict: Any | None,
        tab_indent: int = 4,
        current_indent: int = 0,
        end: str = "\n",
        indent_start: bool = True,
        one_line: bool = False,
        drop_null: bool = False,
    ) -> str:
        """Recursive function to create configuration file"""
        output = ""
        if isinstance(data_dict, dict):
            for k, v in data_dict.items():
                if drop_null and v is None:
                    continue
                if isinstance(v, dict):
                    output += " " * current_indent * int(indent_start)
                    output += f"{k} {{\n"
                    output += NextflowSerial.dumps(
                        v,
                        tab_indent=tab_indent,
                        current_indent=current_indent + tab_indent,
                        end=end,
                        drop_null=drop_null,
                    )
                    output += " " * current_indent
                    output += f"}}{end}"
                elif isinstance(v, list):
                    output += " " * current_indent
                    output += f"{k} = ["
                    vi = []
                    for i in v:
                        oneliner = bool(len(i.keys()) != 1)
                        if isinstance(i, dict):
                            vi.append(
                                "{" * oneliner
                                + NextflowSerial.dumps(
                                    i,
                                    tab_indent,
                                    current_indent=0,
                                    end="",
                                    indent_start=False,
                                    one_line=not oneliner,
                                    drop_null=drop_null,
                                )
                                + "}" * oneliner
                            )
                            continue
                        vi.append(NextflowSerial.dumps(i, tab_indent, current_indent=0, end=end, drop_null=drop_null))
                    output += ", ".join(vi)
                    output += f"]{end}"
                else:
                    output += " " * current_indent * indent_start
                    if one_line:
                        # False is set here to disable quotes on strings
                        output += f"{k}: {NextflowSerial._stringify(v)}{end}"
                    else:
                        output += f"{k} = {NextflowSerial._stringify(v)}{end}"
            return output
        else:
            return NextflowSerial._stringify(data_dict)
