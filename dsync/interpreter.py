def translate(commands):
    commands = commands.split(",")
    if "+" in commands[0][0:1]:
        action = "add"
    elif "*" in commands[0][0:1]:
        action = "update"
    elif "-" in commands[0][0:1]:
        action = "delete"
    else:
        raise ValueError(("Improper Start Character",))
    commands[0] = commands[0].strip()
    commands[0] = commands[0][1:]
    name = commands[0][commands[0].index("[") + 1:commands[0].index("]")]
    if action is "update":
        where = name[name.index("(") + 1:name.index(")")].split("|")
        name = name[0:name.index("(")]
        url = name + "/" + action + "/" + where[0] + "/" + where[1] + "/"
    elif action is "delete":
        where = name[name.index("(") + 1:name.index(")")].split("|")
        name = name[0:name.index("(")]
        url = name + "/" + action + "/" + where[0] + "/" + where[1]
        return url
    else:
        url = name + "/" + action + "/"
    commands[0] = commands[0][commands[0].index("]") + 1:]
    for command in commands:
        pack = command.split("|")
        url += pack[0].strip() + "/" + pack[1].strip() + "/"
    url = url.replace(" ", "%20")
    return url[0:len(url) - 1]
