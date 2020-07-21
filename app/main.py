import argparse
import logging
import sys

import pegovka_calculus


def main():
    args = parse_args()
    if args.recursion_limit:
        sys.setrecursionlimit(args.recursion_limit)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(relativeCreated)s %(funcName)s: %(message)s"
    )
    args.function(args)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pegovka calculus evaluator."
    )
    parser.add_argument(
        "--recursion-limit", metavar="N", type=int, default=1000000,
        help="Set python recursion limit (default: %(default)s)."
    )
    parser.add_argument(
        "--log-level", metavar="NAME", default="INFO",
        help="Set logging level (default: %(default)s)."
    )
    parser.add_argument(
        "--module-path", metavar="PATH", default="galaxy.txt",
        help="Path to module with definitions (default: %(default)s)."
    )
    parser.add_argument(
        "--proxy-url", metavar="URL",
        default="https://icfpc2020-api.testkontur.ru",
        help="Proxy URL (default: %(default)s)."
    )
    parser.add_argument(
        "--player-key", metavar="KEY", help="Player key."
    )

    subparsers = parser.add_subparsers(metavar="COMMAND")

    dump_ast_parser = subparsers.add_parser(
        "dump-ast", help="Dump AST."
    )
    dump_ast_parser.add_argument(
        "symbol", help="Symbol string."
    )
    dump_ast_parser.set_defaults(function=dump_ast_command)

    eval_parser = subparsers.add_parser(
        "eval", help="Evaluate expression."
    )
    eval_parser.add_argument(
        "expression", help="Expression string."
    )
    eval_parser.set_defaults(function=eval_command)

    interact_loop_parser = subparsers.add_parser(
        "interact-loop", help="Run interact loop."
    )
    interact_loop_parser.add_argument(
        "protocol", help="Protocol name."
    )
    interact_loop_parser.set_defaults(function=interact_loop_command)

    return parser.parse_args()


def dump_ast_command(args):
    symbol = pegovka_calculus.Symbol(args.expression)
    print(pegovka_calculus.load(args.module_path)[symbol])


def eval_command(args):
    evaluator = pegovka_calculus.Evaluator(
        args.module_path, args.proxy_url, args.player_key
    )
    evaluator.eval(args.expression)


def interact_loop_command(args):
    evaluator = pegovka_calculus.Evaluator(
        args.module_path, args.proxy_url, args.player_key
    )
    evaluator.interact_loop(args.protocol)


if __name__ == "__main__":
    main()
