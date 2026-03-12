from typing import Any, Optional

class NextflowSerial:
    def __init__(self, data_dict: Optional[dict], tab_indent: Optional[int] = 4):
        self.data_dict = data_dict

    def __getitem__(self, key: Optional[Any]) -> Any:
        """Returns value from data"""
        return self.data_dict[key]

    def __setitem__(self, key: Optional[Any], value: Optional[any]) -> None:
        """Sets value in data"""
        self.data_dict[key] = value

    @staticmethod
    def _stringify(data: Optional[Any]) -> str:
        """Return nextflow compatible value"""
        if isinstance(data, str):
            return f"'{data}'"
        if isinstance(data, bool):
            return 'true' if data else 'false'
        if isinstance(data, type(None)):
            return 'null'
        return str(data) # Fallback on the Python str function if no matches
    
    @staticmethod
    def dumps(data_dict: Optional[Any], tab_indent: Optional[int], current_indent: Optional[int], end: Optional[str] = '\n') -> str:
        """Recursive function to create configuration file"""
        output = ""
        if isinstance(data_dict, dict):
            for k, v in data_dict.items():
                if isinstance(v, dict):
                    output += " "*current_indent
                    output += f"{k} {{\n"
                    output += NextflowSerial.dumps(v, tab_indent = tab_indent, current_indent = current_indent + tab_indent, end = end)
                    output += " "*current_indent
                    output += f"}}{end}"
                elif isinstance(v, list):
                    output += " "*current_indent
                    output += f"{k} = ["
                    vi = []
                    for i in v:
                        if isinstance(i, dict):
                            vi.append("{" + NextflowSerial.dumps(i, tab_indent, current_indent=0, end='') + "}")
                            continue
                        vi.append(NextflowSerial.dumps(i, tab_indent, current_indent=0, end = end))
                    output += ", ".join(vi)
                    output += f"]{end}"
                else:
                    output += " "*current_indent
                    output += f"{k} = {NextflowSerial._stringify(v)}{end}"
            return output
        else:
            return NextflowSerial._stringify(data_dict)
