# Path Resolver

Goals:
* parse
* format
* relative templates
    root: "/root"
    relative: "/temp"
    path: "@root/folder/@relative"
* can have a path set as root which all resolved paths are joined to. This is
  done by a keyword to format which if not given, defaults to the set value, but
  can be explicitly set to something else or to None which enforces no root, eg:
    Pathresolver.set_root("/projects")
    template.format() --> "/projects/..."
* token options:
    default:
    type:
    choices: <-- introduces complications for searching (glob each, or glob wildcard and validate)
* nested_fields - much like relative templates
