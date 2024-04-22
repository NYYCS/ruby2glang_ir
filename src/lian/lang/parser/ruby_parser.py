#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type == "comment"

    def is_identifier(self, node):
        return node.type == "identifier"

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "integer": self.regular_number,
            "float": self.regular_number,
            # "complex": self.complex,
            # "rational": self.rational,
            "string": self.string_literal,
            "true": self.regular_literal,
            "false": self.regular_literal,
            "array": self.array,
            "hash": self.hash,
        }

        return LITERAL_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def regular_number(self, node, statements, replacement):
        value = self.read_node_text(node)
        value = self.common_eval(value)
        return str(value)

    def string_literal(self, node, statements, replacement):
        replacement = []
        for child in node.named_children:
            self.parse(child, statements, replacement)

        ret = self.read_node_text(node)
        if replacement:
            for r in replacement:
                (expr, value) = r
                ret = ret.replace(self.read_node_text(expr), value)

        return self.escape_string(ret)

    def regular_literal(self, node, statements, replacement):
        return self.read_node_text(node)

    def array(self, node, statements, replacement):
        tmp_var = self.tmp_variable(statements)
        statements.append({"new_array": {"type": "", "target": tmp_var}})

        index = 0
        for child in node.named_children:
            if self.is_comment(child):
                continue

            shadow_child = self.parse(child, statements)
            statements.append({"array_write": {"array": tmp_var, "index": str(index), "source": shadow_child}})
            index += 1

        return tmp_var

    def hash(self, node, statements, replacement):
        tmp_var = self.tmp_variable(statements)
        statements.append({"new_map": {"type": "", "target": tmp_var}})

        index = 0
        for child in node.named_children:
            if self.is_comment(child):
                continue 
            key = self.find_child_by_field(child, "key")
            shadow_key = self.parse(key, statements)

            value = self.find_child_by_field(child, "value")
            shadow_value = self.parse(value, statements)

            statements.append({"map_write": {"map": tmp_var, "key": shadow_key, "value": shadow_value}})
            index += 1

        return tmp_var

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
            "method": self.method_declaration,
        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

    def method_declaration(self, node, statements):
        child = self.find_child_by_field(node, "type")
        mytype = self.read_node_text(child)

        child = self.find_child_by_field(node, "name")
        name = self.read_node_text(child)

        new_parameters = []
        init = []
        child = self.find_child_by_field(node, "parameters")
        if child and child.named_child_count > 0:
            # need to deal with parameters
            for p in child.named_children:
                if self.is_comment(p):
                    continue

                self.parse(p, init)
                if len(init) > 0:
                    new_parameters.append(init.pop())

        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                if self.is_comment(stmt):
                    continue

                self.parse(stmt, new_body)

        statements.append(
            {"method_decl": {"attr": "", "data_type": "", "name": name, "type_parameters": "",
                             "parameters": new_parameters, "init": init, "body": new_body}})

    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "binary": self.binary_expression,
            "unary": self.unary_expression,
            "conditional": self.conditional_expression,
            "case": self.case_expression,
            "assignment": self.assignment_expression,
            "operator_assignment": self.operator_assignment_expression,
            "call": self.call_expression,
            "element_reference": self.element_reference_expression,
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def binary_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        operator = self.find_child_by_field(node, "operator")

        shadow_operator = self.read_node_text(operator)

        shadow_left = self.parse(left, statements)
        shadow_right = self.parse(right, statements)

        tmp_var = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_left,
                                           "operand2": shadow_right}})

        return tmp_var
    
    def unary_expression(self, node, statements):
        operand = self.find_child_by_field(node, "operand")
        shadow_operand = self.parse(operand, statements)
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)

        tmp_var = self.tmp_variable(statements)

        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_operand}})

        return tmp_var

    def conditional_expression(self, node, statements):
        condition = self.find_child_by_field(node, "condition")
        consequence = self.find_child_by_field(node, "consequence")
        alternative = self.find_child_by_field(node, "alternative")

        condition = self.parse(condition, statements)

        body = []
        elsebody = []
        tmp_var = self.tmp_variable(statements)

        expr1 = self.parse(consequence, body)
        body.append({"assign_stmt": {"target": tmp_var, "operand": expr1}})

        expr2 = self.parse(alternative, elsebody)
        elsebody.append({"assign_stmt": {"target": tmp_var, "operand": expr2}})

        statements.append({"if": {"condition": condition, "body": body, "elsebody": elsebody}})

        return tmp_var

    def case_expression(self, node, statements):
        pass

    def assignment_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")

        shadow_right = self.parse(right, statements)

        if left.type == "element_reference":
            shadow_map, shadow_key = self.parse_element_reference(left, statements)
            statements.append(
                    {"map_write": {"map": shadow_map, "key": shadow_key, "value": shadow_right}})
            return shadow_right

        if left.type == "call":
            name = self.find_child_by_field(left, "method")
            shadow_name = self.parse(name)

            myobject = self.find_child_by_field(left, "receiver")
            shadow_object = self.parse_call_receiver(myobject, statements)

            statements.append(
                    {"field_write": {"receiver_object": shadow_object, "field": shadow_name, "source": shadow_right}})
                    
            return shadow_right

        shadow_left = self.read_node_text(left)

        statements.append({"assign_stmt": {"target": shadow_left, "operand": shadow_right}})

        return shadow_left

    def operator_assignment_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator).replace("=", "")

        shadow_right = self.parse(right, statements)
        shadow_left = self.read_node_text(left)

        statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                            "operand": shadow_left, "operand2": shadow_right}})

        return shadow_left
        

    def call_expression(self, node, statements):
        name = self.find_child_by_field(node, "method")
        shadow_name = self.parse(name, statements)

        shadow_object = ""
        myobject = self.find_child_by_field(node, "receiver")
        
        if myobject:
            shadow_object = self.parse_call_receiver(myobject, statements)
            tmp_var = self.tmp_variable(statements)
            statements.append(
                {"field_read": {"target": tmp_var, "receiver_object": shadow_object , "field": shadow_name}})
            shadow_name = tmp_var

        args = self.find_child_by_field(node, "arguments")
        args_list = []

        if args:
            for child in args.named_children:
                if self.is_comment(child):
                    continue

                shadow_variable = self.parse(child, statements)
                if shadow_variable:
                    args_list.append(shadow_variable)

        tmp_return = self.tmp_variable(statements)
        statements.append({"call_stmt": {"target": tmp_return, "name": shadow_name, "type_parameters": "", "args": args_list}})

        return self.global_return()

    def element_reference_expression(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        shadow_map, shadow_key = self.parse_element_reference(node, statements)
        statements.append({"map_read": {"target": tmp_var, "map": shadow_map, "key": shadow_key}})
        return tmp_var

    def case_expression(self, node, statements):
        pass

    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            "if": self.if_statement,
            "for": self.for_statement
        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)

    def if_statement(self, node, statements):
        condition_part = self.find_child_by_field(node, "condition")
        true_part = self.find_child_by_field(node, "consequence")
        false_part = self.find_child_by_field(node, "alternative")

        true_body = []

        shadow_condition = self.parse(condition_part, statements)
        self.parse(true_part, true_body)
        if false_part:
            false_body = []
            self.parse(false_part, false_body)
            statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body, "else_body": false_body}})
        else:
            statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body}})

    def while_statement(self, node, statements):
        condition = self.find_child_by_field(node, "condition")
        body = self.find_child_by_field(node, "body")

        new_condition_init = []

        shadow_condition = self.parse(condition, new_condition_init)

        new_while_body = []
        self.parse(body, new_while_body)

        statements.extend(new_condition_init)
        new_while_body.extend(new_condition_init)

        statements.append({"while_stmt": {"condition": shadow_condition, "body": new_while_body}})

    def for_statement(self, node, statements):
        pattern = self.find_child_by_field(node, "pattern")

        shadow_names = []
        if pattern.named_child_count == 0:
            shadow_name = self.parse(pattern)
            shadow_names.append(shadow_name)
        else:
            for child in pattern.named_children:
                shadow_name = self.parse(child)
                shadow_names.append(shadow_name)

        tmp_var = self.tmp_variable(statements)

        value = self.find_child_by_field(node, "value")
        shadow_value = self.parse(value, statements)

        for_body = []

        for index, shadow_name in enumerate(shadow_names):
            tmp_var2 = self.tmp_variable(statements)
            statements.append({ "array_read": { "target": tmp_var2, "array": tmp_var, "index": index }})
            statements.append({ "assign_stmt": {"target": shadow_name, "operand": tmp_var2 }})

        body = self.find_child_by_field(node, "body")
        self.parse(body, for_body)

        statements.append({"forin_stmt":
                               {"attr": "",
                                "data_type": "",
                                "name": tmp_var,
                                "target": shadow_value,
                                "body": for_body}})

    def parse_call_receiver(self, node, statements):
        receiver = self.find_child_by_field(node, 'receiver')
        remaining_content = self.read_node_text(node).split('.')

        receiver_object = remaining_content[0]
        remaining_content = remaining_content[1:]

        for shadow_name in remaining_content:
            tmp_var = self.tmp_variable(statements)
            statements.append(
                {"field_read": {"target": tmp_var, "receiver_object": receiver_object , "field": shadow_name}})
            receiver_object = tmp_var

        return receiver_object


    def parse_element_reference(self, node, statements):
        myobject = self.find_child_by_field(node, "object")
        shadow_object = self.parse(myobject, statements)

        # Ruby grammar.js doesn't put a named field for index
        # TODO: make this work for multikeys reference
        key = node.children[2:-1][0]
        shadow_key = self.parse(key, statements)

        return shadow_object, shadow_key
