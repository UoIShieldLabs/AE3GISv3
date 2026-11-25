# Tutorials and scenarios

Both live inside the topology and are edited with `edit_topology`.

## Tutorials (Jupyter-like notebooks for students)
- A tutorial has a `title` and ordered **cells**: `markdown` notes (`source`, Markdown,
  no raw HTML) and `command` cells (`containerId` + `command`). In the Tutorials
  panel, Run types a command cell into that device's normal terminal, so later cells
  run inside what earlier ones started (an `ssh` session, a Python REPL).
- `setup` = what **Configure lab** runs headless before the tutorial: `steps`
  (`{containerId, command}` in order, `set_tutorial_setup`) and background traffic.
- Ops: `add_tutorial {title}`, `add_cell {tutorial, kind, source | device+command,
  after?}`, `update {id: <cell id>, set: {source | command | containerId}}`,
  `remove {ids: [cell or tutorial ids]}`, `set_tutorial_setup {tutorial, steps}`.
- Good tutorials alternate a short note (what and why) with one command, and end
  with a note on what the student should have observed.

## Scenarios (instructor step-through)
- A scenario has **phases**; each phase has ordered **steps** (`containerId`,
  `script` = a command line, optional `args`). `run_scenario_phase` runs a phase's
  steps on the deployed lab, in order, and returns each one's output.
- Ops: `add_scenario {name}`, `add_phase {scenario, name}`, `add_step {phase,
  device, script, args?}`, `remove_step {phase, index}`, `update`, `remove`.

## Lessons
An instructor's topology can be **published** (`publish_topology`): their students
see it as a lesson and each gets their own copy. Unpublishing removes the copies.
