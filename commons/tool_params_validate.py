
class APITest:

    def validate_tool_validator_from_schema(self,tools_schema):
        tool_rules = {}

        for tool in tools_schema:
            func = tool['function']
            name = func['name']
            params = func['parameters']

            required = params.get('required', [])
            properties = params.get('properties', {})

            type_map = {}
            for key, prop in properties.items():
                t = prop.get('type')
                if t =='integer':
                    type_map[key] = int
                elif t =='string':
                    type_map[key] = str
                elif t =='boolean':
                    type_map[key] = bool
                elif t =='float':
                    type_map[key] = float
                else:
                    type_map[key] = None

            tool_rules[name] = {
                'required': required,
                "types": type_map,
            }
        return tool_rules

    def check_tool(self, tool_name, tool_args, tool_rules):
        if tool_name not in tool_rules:
            return False, f'工具不存在: {tool_name}'
        rule = tool_rules[tool_name]
        required = rule['required']
        type_map = rule['types']

        for field in required:
            if field not in tool_args:
                return False, f'缺失必填参数:{field}'

        for field, expected_type in type_map.items():
            if field not in tool_args:
                continue

            real_value = tool_args[field]

            if expected_type == int:
                if isinstance(real_value, str) and real_value.isdigit():
                    real_value = int(real_value)
                    tool_args[field] = real_value

            if not isinstance(real_value, expected_type):
                raise TypeError(f"{field} 应为 {expected_type}，实际是 {type(real_value)}")


        return True, '校验通过!'



