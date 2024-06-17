from app.transformer import *
from app.validator import validate
from typing import List, Any, Tuple

from lark import Lark
import os
import html


end_task = "{0}((End))"
task_block = "{0}({1})"
input_block = "{0}({1})"
callbk_block = "{0}[/{1}\\]"
success_arrow = "-->"
fail_arrow = "-.->|{0}|"
default_arrow = "==>"

cbk = "cbk"
inp = "inp"
tsk = "task"

end_style_class = "endst"
node_styling = {
    end_style_class: f"classDef {end_style_class} \\",
    inp: f"classDef {inp} \\",
    cbk: f"classDef {cbk} \\",
    tsk: f"classDef {tsk} \\",
}

s_link_style = "linkStyle {0} stroke:green;"
e_link_style = "linkStyle {0} stroke:red;"
d_link_style = "linkStyle {0} stroke:black,stroke-width:5px;"


class VizGenerator:
    def __init__(self, appmodel: App = None, dsl: str = None):
        self.appmodel = appmodel

        if appmodel is None:
            is_valid, self.appmodel, _ = validate(dsl)

            if not is_valid:
                raise Exception("dsl malformed, cannot generate diagram")

    def get_state_from_name(self, step_name: str) -> Any:
        t_msg_match = [x for x in self.appmodel.tasks if x.name == step_name]
        c_msg_match = [x for x in self.appmodel.callbacks if x.name == step_name]
        i_msg_match = [x for x in self.appmodel.inputs if x.name == step_name]

        state_obj = None
        if len(t_msg_match) > 0:
            state_obj = (t_msg_match[0], tsk)
        elif len(c_msg_match) > 0:
            state_obj = (c_msg_match[0], cbk)
        elif len(i_msg_match) > 0:
            state_obj = (i_msg_match[0], inp)

        return state_obj

    def get_next_state(self, step_name: str) -> str:
        for idx, step in enumerate(self.appmodel.state_list):
            if step == step_name:
                state_obj, state_type = self.get_state_from_name(step_name)
                if state_type == tsk and state_obj.type == StateType.end:
                    return "end"

                if idx < len(self.appmodel.state_list) - 1:
                    return self.appmodel.state_list[idx + 1]
                else:
                    return "end"

        return "end"

    def get_next_success(self, success_str: str) -> str:
        if success_str:
            success_parts = success_str.split(" ")
            for step in self.appmodel.state_list:
                if step in success_parts:
                    yield step

    def get_next_errors(self, error_blocks: list[Error]) -> str:
        if error_blocks:
            for eb in error_blocks:
                if eb.action != "none":
                    yield eb.action

    def get_message_value(self, msg_block: VarDesc) -> str:
        if msg_block.vtype != ObjType.var:
            return str(msg_block.val)

        for m in self.appmodel.messages:
            if m.val == msg_block.val:
                return m.desc

        return ""

    def escape_str(self, s):
        special_chars_mapping = {
            " ": "&nbsp;",
            "!": "&excl;",
            "@": "&commat;",
            "#": "&num;",
            "$": "&dollar;",
            "%": "&percnt;",
            "^": "&Hat;",
            "*": "&ast;",
            "(": "&lpar;",
            ")": "&rpar;",
            "_": "&lowbar;",
            "+": "&plus;",
            "=": "&equals;",
            "{": "&lcub;",
            "}": "&rcub;",
            "[": "&lsqb;",
            "]": "&rsqb;",
            "|": "&verbar;",
            "\\": "&bsol;",
            ":": "&colon;",
            '"': "&quot;",
            "'": "&apos;",
            "<": "&lt;",
            ">": "&gt;",
            ",": "&comma;",
            ".": "&period;",
            "?": "&quest;",
            "/": "&sol;",
        }
        s = html.escape(s)
        for char, code in special_chars_mapping.items():
            s = s.replace(char, code)
        return s

    def build_tree(self) -> str:
        if self.appmodel is None:
            return ""

        relation_map = {}
        type_map = {}
        task_name_mapping = {}

        k = "a"
        for state in self.appmodel.state_list:
            task_name_mapping[state] = k
            k = chr(ord(k) + 1)

        task_name_mapping["end"] = k

        for state in self.appmodel.state_list:
            state_obj, state_type = self.get_state_from_name(state)
            type_map[state] = state_type

            next_state = self.get_next_state(state)

            if state_type == cbk:
                relation_map[(state, next_state)] = default_arrow
            else:
                slist = list(set(self.get_next_success(state_obj.next_success)))
                elist = list(set(self.get_next_errors(state_obj.next_error)))

                transition_set = False
                if slist == elist:
                    if len(slist) < 1:
                        relation_map[(state, next_state)] = default_arrow
                        transition_set = True
                    elif len(slist) == 1:
                        relation_map[(state, slist[0])] = default_arrow
                        transition_set = True

                if not transition_set:
                    for s in slist:
                        relation_map[(state, s)] = success_arrow

                    if state_obj.next_error:
                        for e in state_obj.next_error:
                            if e.action != "none":
                                ename = e.action
                                edesc = str(e.code)
                                relation_map[(state, ename)] = fail_arrow.format(edesc)

        # print relation
        mermaid_code = []
        mermaid_code.append("flowchart TD")

        for _, style in node_styling.items():
            mermaid_code.append(style)

        # node type
        for state in self.appmodel.state_list:
            st_type = type_map[state]
            st_key = task_name_mapping[state]
            state_obj, state_type = self.get_state_from_name(state)
            state_name = state_obj.name
            if "action" in state_obj.__dict__:
                state_name = state_obj.action if state_obj.action else state_name
            elif "message" in state_obj.__dict__:
                message_val = self.get_message_value(state_obj.message)
                state_name = message_val if message_val else state_name
            state_name = "".join(state_name.split("\n")).replace("\\", "")
            state_name = state_name.replace("\n", "")
            if len(state_name) > 45:
                state_name = self.escape_str(state_name[:45] + "..")
            else:
                state_name = self.escape_str(state_name)

            node_def = None
            node_style = st_type

            if st_type == tsk:
                node_def = task_block.format(st_key, state_name)
            elif st_type == inp:
                node_def = input_block.format(st_key, state_name)
            else:
                node_def = callbk_block.format(st_key, state_name)

            if state.lower() == "end":
                node_style = end_style_class
                node_def = end_task.format(st_key)

            mermaid_code.append(node_def + ":::" + node_style)

        # relations
        is_end_present = any([t[1] == "end" for t, e in relation_map.items()])
        link_counter = 0
        s_link = []
        e_link = []
        d_link = []

        relation_map_tuple = sorted(
            relation_map.items(), key=lambda t: task_name_mapping[t[0][1]]
        )
        for transition, edge in relation_map_tuple:
            src, dest = transition
            s = task_name_mapping[src]
            d = task_name_mapping[dest]

            # dont have edge from end to end
            if not (is_end_present and s == d and s == task_name_mapping["end"]):
                mermaid_code.append(s + edge + d)

                if edge == default_arrow:
                    d_link.append(link_counter)
                elif edge == success_arrow:
                    s_link.append(link_counter)
                else:
                    e_link.append(link_counter)

                link_counter += 1

        # edge styling
        for link_lst, link_stl in [
            (s_link, s_link_style),
            (e_link, e_link_style),
            (d_link, d_link_style),
        ]:
            if len(link_lst) > 0:
                link_lst_str = ",".join([str(l) for l in link_lst])
                mermaid_code.append(link_stl.format(link_lst_str))

        # end styling
        if is_end_present:
            end_def = end_task.format(task_name_mapping["end"])
            end_style = end_style_class
            mermaid_code.append(end_def + ":::" + end_style)

        return "\n".join(mermaid_code)
