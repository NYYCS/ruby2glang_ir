# 编译实验：AST转IR——declaration

## RUBY小组成员

- 黄宇悦 20300246005
- 黄婧媛 21300246010
- 田娜 21307130437

## 实验思路

本次实验需要将ruby语法中的 `declaration` 部分转化为GLang IR。基于之前实验的经验，我们根据已定义的一个方法`check_declaration_handler`，该方法接受一个`node`作为参数。在方法内部，我们定义了一个名为`DECLARATION_HANDLER_MAP`的字典，该字典将不同类型的表达式(declaration)映射到相应的处理方法上。如下：

```python
def check_declaration_handler(self, node):
    DECLARATION_HANDLER_MAP = {
        "method": self.method_declaration,
        "lambda": self.lambda_declaration,
        "class": self.class_declaration,
        "singleton_class": self.singleton_class_declaration,
        "module": self.module_declaration,
    }
    return DECLARATION_HANDLER_MAP.get(node.type, None)
```

接着，我们参考`java_parser.py`以及`ruby_grammar.js`来完成`ruby_parser.py`中所需要的方法。

-----

### (1) method_declaration

对`method`节点，调用`method_declaration`用于解析函数声明，先去了解GLang IR文档中关于`method_decl`的描述，主要包括以下组成部分：<br>

- `attr`: 函数的属性，例如`public\static`等
- `data_type`: 返回值的数据类型
- `name`: 函数名称
- `parameters`: 参数列表，为列表
- `init`: 参数初始化内容，为列表
- `body`: 内部具体指令，为列表

对于`ruby`语言， 

```ruby
def sum(a, b)
  a + b  
end
```

- `attr`: Ruby没有像Java那样的修饰符（如public、static等）来控制方法的属性，所以为`""`。
- `data_type`: 在Ruby中，方法声明中没有指定返回值的数据类型，所以也为`""`。
- `name`: 可以通过先找到当前节点下名为`name`的子节点，读取文本信息即为函数的名称，如示例中的`"sum"`。

```python
name = self.find_child_by_field(node, "name")
shadow_name = self.read_node_text(name)
```

- `parameters`: 先找到名为`parameters`的子节点。由于最终对应的是个`list`，里面每一项都是`parameter_decl: []`。通过对`ruby_grammar.js`的分析，如下，`parameters`字段是可选的，所以要先判断这个子节点是否存在，如果是，则进行后面的处理。

```js
// ruby_grammar.js
method: $ => seq('def', $._method_rest),

_method_rest: $ => seq(
      field('name', $._method_name),
      choice(
        $._body_expr,
        seq(
          field('parameters', alias($.parameters, $.method_parameters)),
          choice(
            seq(optional($._terminator), optional(field('body', $.body_statement)), 'end'),
            $._body_expr,
          ),
        ),
        seq(
          optional(field('parameters', alias($.bare_parameters, $.method_parameters)),),
          $._terminator,
          optional(field('body', $.body_statement)),
          'end',
        ),
      ),
    ),
```

依次遍历所有的`parameters`节点的所有子节点。判断参数类型，如果是`identifier`则直接读取节点内容加入`new_parameters`参数列表，这种情况属于固定参数。

```python
# def lambda_declaration(self, node, statements): 
# ...
for parameter in parameters.named_children:
    if parameter.type == 'identifier':
        shadow_parameter = self.read_node_text(parameter)
        new_parameters.append(shadow_parameter)
```

如果类型是`optional_parameter`，这种该情况下是默认参数，如果调用方法时没有提供对应的参数，则使用默认值。该参数节点下还有子节点，名称分别为`name`和`value`。见如下的ruby例子：

```ruby
def greet(name = "stranger")
  puts "Hello, #{name}!"
end
```

这个例子中，`name`就是`name`，`value`是`"stranger"`。可以看做`assign`语句。处理方式如下：

获取名为`name`的子节点，获取节点内容，加入参数列表中。然后获取名为`value`的子节点，调用`parser`函数进一步解析，且新生成的语句保存在`new_init`中，返回值保存在变量`shadow_value`中。

最后，使用`shadow_parameter`和`shadow_value`生成新的语句`assign_stmt`（两个变量分别表示`target`和`operand`），加入`new_init`中。

```python
    elif parameter.type == 'optional_parameter':
        parameter_name = self.find_child_by_field(parameter, 'name')
        shadow_parameter = self.read_node_text(parameter_name)
        new_parameters.append(shadow_parameter)
    
        new_init = []
    
        value = self.find_child_by_field(parameter, 'value')
        shadow_value = self.parse(value, new_init)
    
        new_init.append({'assign_stmt': {'target': shadow_parameter, 'operand': shadow_value}})
    
        init.extend(new_init)
```

- `init`: 参数初始化内容，在之前对`parameters`的分析中以及得到，如果有参数初始化，即各个`parameter`的类型为`optional_parameter`，将`new_init`依次添加到`init`中。
- `body`: 为具体的指令。只需在`node`下找到名为`body`的子节点，如果节点存在，则依次遍历它之下的子节点，如果是注释则跳过，否则调用`parser`函数解析，
所有生成的语句加入`new_body`中。

```python
new_body = []
child = self.find_child_by_field(node, "body")
if child:
    for stmt in child.named_children:
        if self.is_comment(stmt):
            continue

        self.parse(stmt, new_body)
```

最后，使用通过以上操作获得的`shadow_name`、`new_parameters`、`init`、`new_body`生成`method_decl`语句并加入`statements`中。

```python
statements.append(
    {"method_decl": {"attr": "", "data_type": "", "name": shadow_name,
                     "parameters": new_parameters, "init": init, "body": new_body}})
```

### (2) lambda_declaration

对`lambda`节点，调用`lambda_declaration`用于解析匿名函数声明。 Lambda函数（或匿名函数）是一段没有名字的代码块，可以存储在变量中并多次调用。

```js
lambda: $ => seq(
  '->',
  field('parameters', optional(choice(
    alias($.parameters, $.lambda_parameters),
    alias($.bare_parameters, $.lambda_parameters),
  ))),
  field('body', choice($.block, $.do_block)),
),
```

在`ruby_grammar.js`中的语法规则，以"->"起始，然后包括`parameters`和`body`两个字段。

```ruby
my_lambda = ->(x) { x * 2 }
puts my_lambda.call(5)  # 输出：10
```

`lambda_declaration`也需要处理为函数声明`method_decl`指令。

- 和`method_declaration`一样，`attr`和`data_type`依旧为：`""`。 因为是匿名函数，所以需要一些处理转为有名函数。调用tmp_method()生成函数名`tmp_method`作为`name`。

```python
def lambda_declaration(self, node, statements):
    tmp_method = self.tmp_method()
```

- `parameters`相关信息包含在名为`parameters`的子节点中，同`method_declaration`中的处理一样，`parameters`应为一个列表，依次遍历其下的所有子节点，对每个子节点的类型进行判断，若是普通的`identifier`，则将子节点内容读取出来加入`new_parameters`变量中。若是带默认值的参数，则要进一步读取名为`name`和`value`的子节点，`name`子节点的内容读取出来加入`new_parameters`中，并根据`value`生成`assign_stmt`语句并保存在`init`中。

```python
def lambda_declaration(self, node, statements):
    # ...
    parameters = self.find_child_by_field(node, "parameters")
    new_parameters = []
    init = []
    if parameters:
        # need to deal with parameters
        for parameter in parameters.named_children:
            if parameter.type == 'identifier':
                shadow_parameter = self.read_node_text(parameter)
                new_parameters.append(shadow_parameter)
            elif parameter.type == 'optional_parameter':
                parameter_name = self.find_child_by_field(parameter, 'name')
                shadow_parameter = self.read_node_text(parameter_name)
                new_parameters.append(shadow_parameter)
                new_init = []
                value = self.find_child_by_field(parameter, 'value')
                shadow_value = self.parse(value, new_init)
                new_init.append({'assign_stmt': {'target': shadow_parameter, 'operand': shadow_value}})
                init.extend(new_init)

    
```

- `body`部分与`method_declaration`一样，只需在`node`下找到名为`body`的子节点，如果节点存在，则依次遍历它之下的子节点，如果是注释则跳过，否则调用`parser`函数解析，所有生成的语句加入`new_body`中。

```python
def lambda_declaration(self, node, statements):
    # ...
    new_body = []
    child = self.find_child_by_field(node, "body")
    if child:
        for stmt in child.named_children:
            if self.is_comment(stmt):
                continue
            self.parse(stmt, new_body)
```

最后，使用通过以上操作获得的`tmp_method`、`new_parameters`、`init`、`new_body`生成`method_decl`语句并加入`statements`中。

```python
statements.append(
    {"method_decl": {"attr": "", "data_type": "", "name": tmp_method,
                     "parameters": new_parameters, "init": init, "body": new_body}})
```

### (3) class_declaration

对于`class`节点，`ruby_parser.py` 里的 `class_declaration` 函数来处理类的声明。用于解析表示类声明的树节点，并将这些信息转化为一个特定的字典，然后将这个字典加入到 `statements` 列表中。

```python
def class_declaration(self, node, statements):
        glang_node = defaultdict(list)

        name = self.find_child_by_field(node, 'name')
        shadow_name = self.parse(name)  

        glang_node['name'] = shadow_name

        superclass = self.find_child_by_field(node, 'superclass')
        if superclass:
            superclass = superclass.children[1]
            shadow_superclass = self.read_node_text(superclass)
            glang_node['supers'].append(shadow_superclass)

        body = self.find_child_by_field(node, 'body')

        for child in body.named_children:
            if child.type == 'method':
                method = []
                self.method_declaration(child, method)
                glang_node['member_methods'].append(method.pop())
            if child.type == 'assignment':
                left = self.find_child_by_field(child, 'left')

                right = self.find_child_by_field(child, 'right')
                shadow_right = self.parse(right)

                if left.type == 'instance_variable':
                    shadow_left = self.read_node_text(left)[1:]
                    glang_node['fields'].append({ 'variable_decl': { 'name': shadow_left }}) 
                    glang_node['init'].append({ 'field_write': { 'receiver_object': self.global_self(), 'field': shadow_left, 'source': shadow_right }})
                elif left.type == 'class_variable':
                    shadow_left = self.read_node_text(left)[2:]
                    glang_node['static_init'].append({ 'assign_stmt': { 'target': shadow_left, 'operand': shadow_right }})

        statements.append({ 'class_decl': dict(glang_node) })
```

首先，初始化一个 `defaultdict`，其代表Glang IR的节点，里面包含了类声明的信息。接下来我们从 `node` 中找到表示类名的子节点。使用 `parse` 方法解析这个子节点，获取类名的字符串表示，并存储到 `glang_node` 的 `name` 键中。接着从 `node` 中找到表示父类的子节点。如果找到了父类节点，获取其文本表示并添加到 `glang_node` 的 `supers` 列表中。接下来从 `node` 中找到表示类体的子节点，遍历 `body` 的每个命名子节点。如果子节点是一个方法声明，调用 method_declaration 方法处理这个方法，并将其结果加入到 glang_node 的 'member_methods' 列表中。如果子节点是一个赋值操作，从中提取左赋值表达式和右赋值表达式，并解析右赋值表达式。

如果是左赋值表达式是实例变量，去掉前缀提取其名字，并将其加入到 `glang_node` 的 `fields` 列表中。同时，将初始化操作加入到 `init` 列表中。如果左赋值表达式是类变量，去掉前缀提取其名字，并将其赋值操作加入到 `glang_node` 的 `static_init` 列表中。

最后，将 `glang_node` 转换为一个普通字典，并以 `class_decl` 为键，将其添加到 `statements` 列表中。

### (4) singleton_class_declaration

对于`singleton_class`节点，使用`singleton_class_declaration` 函数来处理。用于处理单例类的声明。

```python
def singleton_class_declaration(self, node, statements):
        self.class_declaration(node, statements)
        statements[-1]['class_decl']['attr'] = ['singleton']
```

`singleton_class`的语法和普通类是一样的，只是在这个类声明的字典中，添加一个 `attr` 键，并将其值设为包含字符串 `singleton` 的列表。

### (5) module_declaration

对于`module`节点，使用`module_declaration` 函数来处理。用于解析表示模块声明的树节点，并将这些信息转化为一个特定的字典，然后将这个表示形式加入到 `statements` 列表中。

```python
def module_declaration(self, node, statements):
        body = self.find_child_by_field(node, 'body')
        new_body = []
        self.parse(body, new_body)
        statements.append({ 'namespace_decl': { 'body': new_body }})
```

首先使用 `find_child_by_field` 方法到表示模块体的子节点 body。接着初始化一个空列表 `new_body`，用于存储解析后的模块体内容。调用 `parse` 方法解析 `body` 节点，并将解析后的结果存储到 `new_body` 列表中。

最后，将一个包含 `namespace_decl` 键的字典添加到 `statements` 列表中。`namespace_decl` 键对应的值是一个字典，其中包含 `body` 键，`body` 键的值是解析后的 `new_body` 列表。
