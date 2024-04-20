#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        # return node.type in ["line_comment", "block_comment"]
        pass

    def is_identifier(self, node):
        return node.type == "identifier"
        pass

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
        }

        return LITERAL_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            "if_statement": self.if_statement,
            "while_statement": self.while_statement,
            "for_statement": self.for_statement,
            "break_statement": self.break_statement,
            "return_statement": self.break_statement,
        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)
    
    # -------- new code --------
    
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
            
    
    def for_statement(self, node, statements):
        init_children = self.find_children_by_field(node, "pattern")
        step_children = self.find_children_by_field(node, "body")

        condition = self.find_child_by_field(node, "value")

        init_body = []
        condition_init = []
        step_body = []

        shadow_condition = self.parse(condition, condition_init)
        for child in init_children:
            self.parse(child, init_body)

        for child in step_children:
            self.parse(child, step_body)

        for_body = []

        block = self.find_child_by_field(node, "body")
        self.parse(block, for_body)

        statements.append({"for_stmt":
                               {"init_body": init_body,
                                "condition": shadow_condition,
                                "condition_prebody": condition_init,
                                "update_body": step_body,
                                "body": for_body}})
    
    def return_statement(self, node, statements):
        shadow_name = ""
        if node.named_child_count > 0:
            name = node.named_children[0]
            shadow_name = self.parse(name, statements)

        statements.append({"return_stmt": {"target": shadow_name}})
        return shadow_name
    
    def break_statement(self, node, statements):
        shadow_name = ""
        if node.named_child_count > 0:
            name = node.named_children[0]
            shadow_name = self.parse(name, statements)

        statements.append({"break_stmt": {"target": shadow_name}})
        