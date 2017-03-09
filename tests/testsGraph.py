
import unittest
import time
from node import DependencyGraph, StaticDependencies, CircularDependencyError

class SimpleGraphTest(unittest.TestCase):
    def test_single_node(self):
        "Test for a single node"
        graph = StaticDependencies([
            ("A", ("B", "C", "D")),
            ("B", ("C", "D")),
            ("D", ("E",))
        ])

        dep_graph = DependencyGraph(["A"], plugins=[graph,])
        self.assertEqual(len(dep_graph.vertices), 6)
        self.assertEqual(len(dep_graph.nodes), 5)

        self.assertEqual({"B", "C", "D", "E"},
                         set(dep_graph.dependencies("A", True)))

        self.assertEqual({"C", "D", "E"},
                         set(dep_graph.dependencies("B", True)))

        self.assertEqual(set(),
                         set(dep_graph.dependencies("C", True)))

        self.assertEqual({"E"},
                         set(dep_graph.dependencies("D", True)))
        self.assertEqual(1+1, 2)

    def test_multi_nodes(self):
        "Test for two non-connected nodes"

        graph = StaticDependencies([
            ("A", ("B", "C", "D")),
            ("1", ("2", "3")),
        ])

        dep_graph = DependencyGraph(["A", "1"], plugins=[graph,])
        self.assertEqual(len(dep_graph.vertices), 5)
        self.assertEqual(len(dep_graph.nodes), 7)

        self.assertEqual({"B", "C", "D"},
                         set(dep_graph.dependencies("A", True)))

        self.assertEqual({"2", "3"},
                         set(dep_graph.dependencies("1", True)))

    def test_dependant_nodes(self):
        "Test for two connected nodes"
        graph = StaticDependencies([
            ("A", ("1", "B")),
            ("1", ("2", "3")),
        ])

        dep_graph = DependencyGraph(["A", "1"], plugins=[graph,])
        self.assertEqual(len(dep_graph.vertices), 4)
        self.assertEqual(len(dep_graph.nodes), 5)

        self.assertEqual({"1", "B", "2", "3"},
                         set(dep_graph.dependencies("A", True)))

        self.assertEqual({"2", "3"},
                         set(dep_graph.dependencies("1", True)))

    def test_shared_nodes(self):
        "Test with nodes having same dependencies patterns"

        graph = StaticDependencies([
            ("A", ("B", "C", "D")),
            ("1", ("2", "3", "C")),
        ])

        dep_graph = DependencyGraph(["A", "1"], plugins=[graph,])
        self.assertEqual(len(dep_graph.vertices), 6)
        self.assertEqual(len(dep_graph.nodes), 7)

        self.assertEqual({"B", "C", "D"},
                         set(dep_graph.dependencies("A", True)))

        self.assertEqual({"2", "3", "C"},
                         set(dep_graph.dependencies("1", True)))

    def test_double_nodes(self):
        "Test with nodes, with some of them being in double"

        graph = StaticDependencies([
            ("A", ("C", "D")),
            ("A", ("B", "C")),
        ])

        dep_graph = DependencyGraph(["A"], plugins=[graph,])
        self.assertEqual(len(dep_graph.vertices), 3)
        self.assertEqual(len(dep_graph.nodes), 4)

        self.assertEqual({"B", "C", "D"},
                         set(dep_graph.dependencies("A", True)))


    def test_lots_nodes(self):
        "Test with a lots of nodes"
        deps = []
        deps_nb = 500
        for i in range(deps_nb):
            deps.append((str(i), [str(v) for v in list(range(i+1, deps_nb))]))

        graph = StaticDependencies(deps)
        dep_graph = DependencyGraph(["0"], plugins=[graph,])
        self.assertEqual(len(dep_graph.nodes), deps_nb)
        self.assertEqual(len(dep_graph.vertices), (deps_nb-1) * (deps_nb/2))

    def test_circular_dependency(self):
        "Ensures that an error is raised on circular dependency"

        graph = StaticDependencies([
            ("A", ("C", "D")),
            ("D", ("A")),
        ])

        with self.assertRaises(CircularDependencyError):
            DependencyGraph(["A"], plugins=[graph,])
