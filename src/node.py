"""Low-level api to work with relationships"""
import functools
import itertools

class BaseFilter:
    "Base filter that accepts one argument"
    def __init__(self, **query):
        assert len(query) == 1
        for key, value in query.items():
            self.key = key
            self.value = value

    @staticmethod
    def parse_key(key):
        "Parses the key to remove the __ if there is one"
        return key.split("__")[0]

    def match(self, value):
        "Checks wether value matches this filter"
        parsed_key = self.parse_key(self.key)
        if parsed_key != "_self":
            value = getattr(value, parsed_key, None)

        if value is None:
            return False

        if self.key.endswith("__gt"):
            return value > self.value
        elif self.key.endswith("__gte"):
            return value >= self.value
        elif self.key.endswith("__lt"):
            return value < self.value
        elif self.key.endswith("__lte"):
            return value <= self.value
        elif self.key.endswith("__ne"):
            return value != self.value
        else:
            return value == self.value


class AndFilter(BaseFilter):
    "Composite filter that combines two filters"

    def __init__(self, filters, **query):
        self.filters = filters
        for key, value in query.items():
            self.filters.append(BaseFilter(**{key:value}))

    def match(self, value):
        is_match = True
        for _filter in self.filters:
            is_match &= _filter.match(value)
        return is_match


class OrFilter(AndFilter):
    "Composite filter that combines two filters via an or"

    def match(self, value):
        is_match = False
        for _filter in self.filters:
            is_match |= _filter.match(value)
        return is_match



class Vertex:
    "Represents a dependency link"

    def __init__(self, vertex_type:str, from_node:str, to_node:str, **attributes):
        # Ensures that we won't override our parameters...
        assert "from_node" not in attributes
        assert "to_node" not in attributes
        assert "vertex_type" not in attributes

        self.vertex_type = vertex_type
        self.from_node = from_node
        self.to_node = to_node

        for key, value in attributes.items():
            setattr(self, key, value)

    def __eq__(self, other):
        if isinstance(other, Vertex):
            return (self.vertex_type == other.vertex_type
                    and self.from_node == other.from_node
                    and self.to_node == other.to_node)

    def __hash__(self):
        return hash((self.vertex_type, self.from_node, self.to_node))

    def __str__(self):
        return "(%s) --> (%s)" % (self.from_node, self.to_node)

class CircularDependencyError(BaseException):
    pass

class DependencyGraph:

    def __init__(self, nodes, plugins):
        self.nodes = set(nodes)
        self.plugins = plugins

        def generate_vertices():
            nodes = list(self.nodes)
            while nodes:
                yield from self.build_vertices(nodes.pop())
        self.vertices = set(generate_vertices())

        if not self.is_acyclic():
            raise CircularDependencyError()

    def __str__(self):
        return "\n".join([str(vertex) for vertex in self.vertices])

    def is_acyclic(self):
        "Checks for circular dependencies"
        nodes = []

        # We build an index
        connected_to = {node: set() for node in self.nodes}
        from_nodes = {node: set() for node in self.nodes}
        for vertice in self.vertices:
            connected_to[vertice.to_node].add(vertice)
            from_nodes[vertice.from_node].add(vertice)

        for node in self.nodes:
            # Only nodes that don't have someone dependent on
            if len(connected_to[node]) == 0:
                nodes.append(node)

        vertices = list(self.vertices)
        deleted_vertices = set()

        while nodes:
            node = nodes.pop()

            connected = from_nodes[node] - deleted_vertices
            for vertice in connected:
                deleted_vertices.add(vertice)
                if not connected_to[node] - deleted_vertices:
                    nodes.append(vertice.to_node)
        return len(vertices) == len(deleted_vertices)

    def build_vertices(self, node):
        plugins = filter(lambda p: p.can_create_vertex(node), self.plugins)
        for plugin in plugins:
            for vertex in plugin.vertices(node):
                if vertex.to_node not in self.nodes:
                    self.nodes.add(vertex.to_node)
                    # I know, we are limited by recursions.
                    # Fix it when it is a problem
                    yield from self.build_vertices(vertex.to_node)
                yield vertex

    def dependencies(self, node, follow=False):
        "Returns dependencies of a node, either all or direct"
        vertices = filter(lambda v: v.from_node == node, self.vertices)
        for vertex in vertices:
            yield vertex.to_node
            if follow:
                yield from self.dependencies(vertex.to_node, follow)


class Plugin:
    "Represents a plugin"
    file_extensions = "*"

    def __init__(self, **kwargs):
        for key, value in kwargs:
            setattr(self, key, value)

    def vertices(self, node):
        "Yields vertices for a node"

        raise NotImplementedError()

    def can_create_vertex(self, node):
        "Checks if this plugin can create links for this type of node"

        if self.file_extensions == "*":
            return True
        if isinstance(self.file_extensions, str):
            return node.name.endswith(self.file_extensions)
        else:
            # If the file extension of the node name is in the plugins file ext
            ends_with = False
            for file_ext in self.file_extensions:
                ends_with = ends_with or node.name.endswith(file_ext)
            return ends_with

class StaticDependencies(Plugin):
    "Plugin to illustrate manual dependencies"
    # Format of a dependency:
    # ("A", ("B", "C", "D"))

    def __init__(self, dependencies, **kwargs):
        self.dependencies = dependencies

    def vertices(self, node):
        for deps in self.dependencies:
            if deps[0] == node:
                for sub_node in deps[1]:
                    yield Vertex("static", node, sub_node)
