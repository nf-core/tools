"""Machine-readable ``--help-json`` help/usage schema for the nf-core CLI.

Adds a global ``--help-json`` flag (via :class:`JSONGroup` / :class:`JSONCommand`)
that prints the *current* command's full help and usage as JSON, together with
a recursive index of all subcommand names. This lets tools and LLMs discover
the CLI one level at a time without parsing rendered ``--help`` text or pulling
the entire command tree into context at once.

A distinct ``--help-json`` name is used (rather than ``--json``) because several
commands already define their own ``--json`` data-output flag.

Usage::

    nf-core --help-json                  # root: options + recursive name index
    nf-core modules --help-json          # modules group and its subcommand names
    nf-core pipelines schema validate --help-json   # full detail for a single command
"""

import json

import rich_click as click
from rich.errors import MarkupError
from rich.text import Text


def _strip_markup(text):
    """Render Rich console markup (``[dim]``, ``\\[default: …]``, …) to plain text."""
    if not text:
        return text
    try:
        return Text.from_markup(text).plain.strip()
    except MarkupError:
        return text.strip()


def _param_to_dict(param, ctx):
    """Convert a Click Option/Argument into a compact, JSON-friendly dict."""
    info = param.to_info_dict()
    type_info = info.get("type") or {}
    fields = {
        "name": info.get("name"),
        "kind": info.get("param_type_name"),  # "option" or "argument"
        "opts": info.get("opts"),
        "type": type_info.get("param_type"),
        "choices": type_info.get("choices"),
        "required": info.get("required") or None,
        "is_flag": info.get("is_flag") or None,
        "multiple": info.get("multiple") or None,
        "help": _strip_markup(info.get("help")),
    }
    # Drop empty/false/None values to keep the output lean
    result = {key: value for key, value in fields.items() if value not in (None, False, [], "")}
    # Keep a real default (including 0 or "") for non-flag params; a flag's False default is implied
    default = info.get("default")
    if default is not None and not info.get("is_flag"):
        result["default"] = default
    return result


def _subcommand_name_tree(group, ctx):
    """Recursively map subcommand names to nested children (names only, no help text).

    Leaf commands map to an empty dict; groups map to a dict of their children.
    """
    tree = {}
    for name in group.list_commands(ctx):
        sub = group.get_command(ctx, name)
        if sub is None:
            continue
        if isinstance(sub, click.Group):
            sub_ctx = click.Context(sub, info_name=name, parent=ctx)
            tree[name] = _subcommand_name_tree(sub, sub_ctx)
        else:
            tree[name] = {}
    return tree


def _emit_json(ctx, param, value):
    """Eager callback for the ``--help-json`` flag: print the schema and exit."""
    if not value or ctx.resilient_parsing:
        return
    click.echo(json.dumps(command_schema(ctx.command, ctx), indent=2, default=str))
    ctx.exit()


# A single shared --help-json option, injected into every command and group below.
JSON_OPTION = click.Option(
    ["--help-json"],
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_emit_json,
    help="Print this command's help/usage as JSON, with a recursive index of subcommand names.",
)

# Universal meta-options excluded from each command's reported parameters.
_META_PARAMS = {"help", JSON_OPTION.name}


def command_schema(cmd, ctx):
    """Build the JSON schema for a single command level.

    Includes the command's own help, usage and full parameter detail. For groups,
    a ``subcommands`` key holds a recursive name-only index of all descendants.
    """
    schema = {
        "name": cmd.name,
        "path": ctx.command_path,
        "help": _strip_markup(cmd.help),
        "usage": " ".join([ctx.command_path, *cmd.collect_usage_pieces(ctx)]),
        "params": [_param_to_dict(param, ctx) for param in cmd.get_params(ctx) if param.name not in _META_PARAMS],
    }
    aliases = getattr(cmd, "aliases", None)
    if aliases:
        schema["aliases"] = list(aliases)
    if isinstance(cmd, click.Group):
        schema["subcommands"] = _subcommand_name_tree(cmd, ctx)
    return schema


def _with_json_option(get_params):
    """Wrap ``get_params`` so the shared ``--help-json`` option appears before ``--help``."""

    def patched(self, ctx):
        params = get_params(self, ctx)
        # Place --help-json just before the trailing --help, without mutating the list
        # returned by Click (which may be the command's own persistent params list).
        return [*params[:-1], JSON_OPTION, *params[-1:]]

    return patched


class JSONCommand(click.RichCommand):
    """A leaf command that exposes the ``--help-json`` schema flag."""

    get_params = _with_json_option(click.RichCommand.get_params)


class JSONGroup(click.RichGroup):
    """A group that exposes ``--help-json`` and propagates these classes to children.

    ``group_class = type`` tells Click that subgroups use this same class, and
    ``command_class`` sets the class for leaf subcommands, so a single ``cls=``
    on the root group is enough to add ``--help-json`` everywhere.
    """

    command_class = JSONCommand
    group_class = type

    get_params = _with_json_option(click.RichGroup.get_params)
