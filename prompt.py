#!/usr/bin/env python

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Example using stdio, Deferreds, LineReceiver and twisted.web.client.

Note that the WebCheckerCommandProtocol protocol could easily be used in e.g.
a telnet server instead; see the comments for details.

Based on an example by Abe Fettig.
"""

import pprint
import json
import logging
logname = 'prompt.log'
logging.basicConfig(
     level=logging.DEBUG,
     filemode='a',
     filename=logname,
     format="%(levelname)s:%(name)s:%(funcName)s:%(message)s")



from neo.Network.NeoNode import NeoNode
from neo.Network.NeoNodeFactory import NeoFactory

from neo.Core.Blockchain import Blockchain
from neo.Implementations.Blockchains.LevelDB.LevelDBBlockchain import LevelDBBlockchain
from neo import Settings

blockchain = LevelDBBlockchain(Settings.LEVELDB_PATH)
Blockchain.RegisterBlockchain(blockchain)

from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet import stdio, reactor, task, threads
from twisted.protocols import basic
from twisted.web import client
import asyncio
from autologging import logged

from pygments.styles.tango import TangoStyle
from pygments.lexers.data import JsonLexer
from prompt_toolkit.styles import style_from_pygments
from prompt_toolkit import prompt
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.layout.lexers import PygmentsLexer
from prompt_toolkit.shortcuts import print_tokens
from prompt_toolkit.token import Token
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.history import InMemoryHistory

example_style = style_from_dict({
    # User input.
    Token:          '#ff0066',

    # Prompt.
    Token.Username: '#884444',
    Token.At:       '#00aa00',
    Token.Colon:    '#00aa00',
    Token.Pound:    '#00aa00',
    Token.Host:     '#000088 bg:#aaaaff',
    Token.Path:     '#884444 underline',
})


@logged
class PromptInterface(object):

    factory = None

    go_on = True

    completer = WordCompleter(['block','tx','header','io','help','state',])

    commands = ['quit','help','show','block {index/hash}', 'header {index/hash}','tx {hash}']

    token_style = style_from_dict({
        Token.Command: '#ff0066',
        Token.Neo: '#0000ee',
        Token.Default: '#00ee00',
        Token.Number: "#ffffff",
    })

    history = InMemoryHistory()

    def get_bottom_toolbar(self, cli=None):
        try:
            return [(Token.Command, 'Progress: '),
                    (Token.Number, str(Blockchain.Default().Height())),
                    (Token.Neo, '/'),
                    (Token.Number, str(Blockchain.Default().HeaderHeight()))]
        except Exception as e:
            print("couldnt get toolbar: %s " % e)
            return []

    def onProtocolConnected(self, protocol):
        if not self.factory:
            self.factory = protocol.factory
        self.__log.debug("PRotocol connected!!")

    def onProtocolError(self, reason):
        self.__log.debug("Protocol exception %s " % vars(reason))

    def quit(self):
        print('Shutting down.  This may take a bit...')
        self.go_on = False
        Blockchain.Default().StopPersist()
        reactor.stop()

    def help(self):
        tokens = []
        for c in self.commands:
            tokens.append((Token.Command, "%s\n" %c))
        print_tokens(tokens, self.token_style)

    def show(self, args):
        what = self.get_arg(args)

        if what=='block':
            return self.show_block(args[1:])
        elif what =='header':
            return self.show_header(args[1:])
        elif what == 'tx':
            return self.show_tx(args[1:])

        item = self.get_arg(args, 1)

        if what == 'state':
            height = Blockchain.Default().Height()
            headers = Blockchain.Default().HeaderHeight()
            print('Progress: %s / %s\n' % (height, headers))
        elif what == 'nodes' or what == 'node':
            if self.factory and len(self.factory.peers):
                for peer in self.factory.peers:
                    print('Peer %s - IO: %s' % (peer.Name(), peer.IOStats()))
                print("\n")
            else:
                print('Not connected yet\n')
        else:
            print("what should i show?  try 'block ID/hash', 'header ID/hash 'tx hash', 'state', 'nodes' ")


    def show_block(self, args):
        item = self.get_arg(args)
        if item is not None:
            block = Blockchain.Default().GetBlock(item)

            if block is not None:
                print(json.dumps(block.ToJson(), indent=4))
            else:
                print("could not locate block %s" % item)
        else:
            print("please specify a block")

    def show_header(self, args):
        item = self.get_arg(args)
        if item is not None:
            header = Blockchain.Default().GetHeaderBy(item)
            if header is not None:
                print(json.dumps(header.ToJson(), indent=4))
            else:
                print("could not locate Header %s \n" % item)
        else:
            print("please specify a header")


    def show_tx(self, args):
        item = self.get_arg(args)
        if item is not None:
            tx,height = Blockchain.Default().GetTransaction(item)
            if height  > -1:
                print(json.dumps(tx.ToJson(), indent=4))
            else:
                print("tx %s not found" % item)
        else:
            print("please specify a tx hash")

    def get_arg(self, arguments, index=0):
        try:
            return arguments[index]
        except Exception as e:
            pass
        return None


    def parse_result(self, result):
        if len(result):
            commandParts = [s.lower() for s in result.split()]
            return commandParts[0], commandParts[1:]
        return None,None

    def run(self):

#        dbloop = task.LoopingCall(Blockchain.Default().PersistBlocks)
#        dbloop.start(.01)

#        reactor.callInThread( Blockchain.Default().PersistBlocks)
#        print("after call in thread!")

        tokens = [(Token.Neo, 'NEO'),(Token.Default,' cli. Type '),(Token.Command, "'help' "), (Token.Default, 'to get started')]
        print_tokens(tokens, self.token_style)
        print("\n")

        while self.go_on:

            result = prompt("neo> ",
                            completer=self.completer,
                            history=self.history,
                            get_bottom_toolbar_tokens=self.get_bottom_toolbar,
                            style=self.token_style)

            command, arguments = self.parse_result(result)
            if command == 'quit' or command == 'exit':
                self.quit()
            elif command == 'help':
                self.help()
            elif command == 'show':
                self.show(arguments)
            elif command == 'block':
                self.show_block(arguments)
            elif command == 'tx':
                self.show_tx(arguments)
            elif command == 'header':
                self.show_header(arguments)
            elif command == None:
                print('please specify a command')
            else:
                print("command %s not found" % command)




def main():
    cli = PromptInterface()

    # start up endpoints
    for bootstrap in Settings.SEED_LIST:
        host, port = bootstrap.split(":")
        print("trying to connect to %s %s " % (host, port))
        point = TCP4ClientEndpoint(reactor, host, int(port))
        d = connectProtocol(point, NeoNode(NeoFactory))
        d.addCallbacks(cli.onProtocolConnected, cli.onProtocolError)

    reactor.callInThread(cli.run)
    reactor.run()

if __name__ == "__main__":
    main()