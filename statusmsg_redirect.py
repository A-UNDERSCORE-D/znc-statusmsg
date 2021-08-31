from typing import TYPE_CHECKING
import znc
import json

if TYPE_CHECKING:
    from typing import Dict, Optional, Union

DEFAULT_FORMAT = '[{prefix}] {msg}'


class statusmsg_redirect(znc.Module):
    module_types = [znc.CModInfo.NetworkModule]

    def __init__(self) -> None:
        self.identifiers = []
        self.format = DEFAULT_FORMAT
        super().__init__()

    def OnLoad(self, sArgs, sMessage):
        if 'identifiers' in self.nv:
            self.identifiers = json.loads(self.nv['identifiers'])

        if 'format' in self.nv:
            self.format = self.nv['format']

        return super().OnLoad(sArgs, sMessage)

    def save(self):
        self.nv['identifiers'] = json.dumps(self.identifiers)
        self.nv['format'] = self.format

    def OnShutdown(self):
        self.save()
        return super().OnShutdown()

    def OnModCommand(self, sCommand: str):
        sCommand = sCommand.strip()
        if sCommand == 'save':
            self.save()

        if sCommand == 'listidentifiers':
            if len(self.identifiers) == 0:
                self.PutModule('No set identifiers, use addidentifier to add some')

            table = znc.CTable()
            table.AddColumn('Identifier')
            for i in self.identifiers:
                table.AddRow()
                table.SetCell('Identifier', i)

            self.PutModule(table)

        elif sCommand.startswith('addidentifier') or sCommand.startswith('delidentifier'):
            split = sCommand.split(' ')
            if len(split) == 2:
                self.handle_add_del(split[0], split[1])

            else:
                self.PutModule("{cmd} requires an argument".format(cmd=split[0]))

        elif sCommand.startswith('setformat'):
            split = sCommand.split(' ', maxsplit=1)
            if len(sCommand) < 2:
                self.PutModule('setformat requires an argument')

            else:
                try:
                    _ = split[1].format(prefix='test', msg='test')

                except KeyError as e:
                    self.PutModule('Unable to format message. Did you typo a formatter? {}'.format(e))

                else:
                    self.format = split[1]
                    self.save()
                    self.PutModule('set {!r} as the in-use format'.format(self.format))

        elif sCommand == 'getformat':
            self.PutModule('{!r} is the currently in-use format'.format(self.format))

        elif sCommand == 'help':
            self.send_help()

        else:
            self.PutModule('Unknown command {!r}. Try help'.format(sCommand))

        return super().OnModCommand(sCommand)

    def handle_add_del(self, cmd: str, name: str):
        if cmd == 'addidentifier':
            self.identifiers.append(name)
            self.PutModule('Added {!r} to identifiers'.format(name))

        elif cmd == 'delidentifier':
            if name not in self.identifiers:
                self.PutModule('{!r} Is not a known identifier'.format(name))
                return

            self.identifiers.remove(name)
            self.PutModule('Removed {!r} from identifiers'.format(name))

    def send_help(self):
        help_table = znc.CTable()
        help_table.AddColumn('Command')
        help_table.AddColumn('Description')

        help_table.AddRow()
        help_table.SetCell('Command', 'Help')
        help_table.SetCell('Description', 'This output')

        help_table.AddRow()
        help_table.SetCell('Command', 'setformat')
        help_table.SetCell(
            'Description', 'Sets the format to modify messages with for specified clients. defaults to {!r}'.format(
                DEFAULT_FORMAT
            )
        )

        help_table.AddRow()
        help_table.SetCell('Command', 'getformat')
        help_table.SetCell('Description', 'Gets the format to modify messages with for specified clients')

        help_table.AddRow()
        help_table.SetCell('Command', 'addidentifier')
        help_table.SetCell('Description', 'Adds a client identifier to the list of identifiers to modify messages for')

        help_table.AddRow()
        help_table.SetCell('Command', 'delidentifier')
        help_table.SetCell(
            'Description', 'Removes a client identifier from the list of identifiers to modify messages for')

        help_table.AddRow()
        help_table.SetCell('Command', 'listidentifiers')
        help_table.SetCell('Description', 'Lists the currently set identifiers')

        help_table.AddRow()
        help_table.SetCell('Command', 'save')
        help_table.SetCell('Description', 'Saves all data (should not be needed)')

        self.PutModule(help_table)

    def OnSendToClientMessage(self, msg: znc.CMessage):
        if not msg.GetType() == msg.Type_Text:
            return

        client = self.GetClient()
        if client is None:
            return znc.CONTINUE

        identifier: str = client.GetIdentifier()
        if identifier == '' or identifier not in self.identifiers:
            return znc.CONTINUE

        # we know we're a PRIVMSG to a channel, so we can start by checking
        # if we're a STATUSMSG and bailing if not
        target: str = msg.GetParam(0)
        # This might be slow. But hopefully it isnt.
        isupport_prefixes = tuple(msg.GetNetwork().GetIRCSock().GetISupport('STATUSMSG'))

        if len(target) == 0 or target[0] not in isupport_prefixes:
            return

        # Okay, STATUSMSG. Lets rewrite history shall we?
        msg.SetParam(0, msg.GetChan().GetName())
        msg.SetParam(1, self.format.format(prefix=target[0], msg=msg.GetParam(1)))
        msg_len = len(msg.ToString())

        if msg_len > 510:
            # we need to trim this, to be sure
            diff = msg_len - 510
            msg.SetParam(1, msg.GetParam(1)[:-diff])

        return super().OnSendToClientMessage(msg)

    if TYPE_CHECKING:
        def PutModule(self, msg: Union[str, znc.CTable]) -> None: ...
        def GetClient(self) -> Optional[znc.CClient]: ...
        nv: 'Dict[str, str]'