# MultiMind

initiates a ovos-core instance per access key, each key gets a unique isolated "Mind"  (multiple connection with same
key allowed)

can be used in a cloud context to provide a dedicated assistant per account, replaces the standard hivemind listener

currently just a proof of concept, stay tuned

## Usage

To launch MultiMind or manage skills per access key

```bash
$ multimind --help

Usage: multimind [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  allow-skill   add a skill to an access key
  list-skills   lists skill for an access key
  remove-skill  remove a skill from an access key
  start         launch MultiMind

```