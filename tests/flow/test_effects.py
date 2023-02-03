import time
import threading
from common import *

GRAPH_ID = "effects"

class testEffects():
    async def wait_for_command(self):
        monitor_response = await self.monitor.next_command()
        return monitor_response
    
    def monitor_thread(self):
        try:
            with self.replica.monitor() as m:
                for cmd in m.listen():
                    if 'GRAPH.EFFECT' in cmd['command']:
                        self.commands.append(cmd['command'][len('GRAPH.EFFECT ' + GRAPH_ID):])
        except:
            pass

    def wait_for_effect(self):
        # wait for monitor to receive commands
        while len(self.commands) != 1:
            time.sleep(1)

        return self.commands.pop()

    def assert_graph_eq(self):
        q = "MATCH (n) RETURN n ORDER BY(n)"
        master_resultset = self.master_graph.query(q).result_set
        replica_resultset = self.replica_graph.query(q, read_only=True).result_set
        self.env.assertEquals(master_resultset, replica_resultset)

        q = "MATCH ()-[e]->() RETURN e ORDER BY(e)"
        master_resultset = self.master_graph.query(q).result_set
        replica_resultset = self.replica_graph.query(q, read_only=True).result_set
        self.env.assertEquals(master_resultset, replica_resultset)

    def __init__(self):
        self.env = Env(decodeResponses=True, env='oss', useSlaves=True)
        self.master = self.env.getConnection()
        self.replica = self.env.getSlaveConnection()
        self.master_graph = Graph(self.master, GRAPH_ID)
        self.replica_graph = Graph(self.replica, GRAPH_ID)
        self.commands = []

        self.monitor_thread = threading.Thread(target=self.monitor_thread)
        self.monitor_thread.start()

    def __del__(self):
        # all done, shutdown replica
        # stops monitor thread
        self.replica.shutdown()
    
    def test01_add_schema_effect(self):
        # test the introduction of a schema by an effect

        # introduce a new label which in turn creates a new schema
        q = "CREATE (:L)"
        self.master_graph.query(q)

        # TODO: validate effect
        effect = self.wait_for_effect()

        self.assert_graph_eq()

        # introduce a new relationship-type which in turn creates a new schema
        q = "CREATE ()-[:R]->()"
        self.master_graph.query(q)

        # TODO: validate effect
        effect = self.wait_for_effect()

        self.assert_graph_eq()

    def test02_add_attribute_effect(self):
        # test the introduction of an attribute by an effect

        # set a new attribute for each supported attribute type
        q = """MATCH (n:L) SET
                n.a = 1,
                n.b = 'str',
                n.c = True,
                n.d = [1, [2], '3'],
                n.e = point({latitude: 51, longitude: 0}),
                n.f=3.14,
                n.empty_string = ''
            """

        self.master_graph.query(q)

        # TODO: validate effect
        effect = self.wait_for_effect()

        self.assert_graph_eq()

    def test03_create_node_effect(self):
        # test the introduction of a new node by an effect

        # empty node
        q0 = """CREATE ()"""

        # label-less node with attributes
        q1 = """CREATE ({
                            i:1,
                            s:'str',
                            b:True,
                            a:[1, [2], '3'],
                            p:point({latitude: 51, longitude: 0}),
                            f:3.14,
                            empty_string: ''
                        })"""

        # labeled node without attributes
        q2 = """CREATE (:L)"""

        # node with multiple labels and attributes
        q3 = """CREATE (:A:B {
                            i:1,
                            s:'str',
                            b:True,
                            a:[1, [2], '3'],
                            p:point({latitude: 51, longitude: 0}),
                            f:3.14,
                            empty_string: ''
                        })"""

        queries = [q0, q1, q2, q3]
        for q in queries:
            self.master_graph.query(q)

            # TODO: validate effect
            effect = self.wait_for_effect()

        self.assert_graph_eq()

    def test04_update_effect(self):
        # test an entity attribute set update by an effect
        q = """MATCH (n:L)
               WITH n
               LIMIT 1
               SET
                    n.a = 2,
                    n.b = 'string',
                    n.c = False,
                    n.d = [[2], 1, '3'],
                    n.e = point({latitude: 41, longitude: 2}),
                    n.f=6.28,
                    n.empty_string = Null"""

        self.master_graph.query(q)

        # TODO: validate effect
        effect = self.wait_for_effect()

        self.assert_graph_eq()

    def test05_set_labels_effect(self):
        # test the addition of a new node label by an effect
        q = """MATCH (n:A:B) SET n:C"""
        result = self.master_graph.query(q)
        self.env.assertEquals(result.labels_added, 1)

        # TODO: validate effect
        effect = self.wait_for_effect()

        self.assert_graph_eq()

    def test06_remove_labels_effect(self):
        # test the removal of a node label by an effect
        q = """MATCH (n:C) REMOVE n:C RETURN n"""
        result = self.master_graph.query(q)
        self.env.assertEquals(result.labels_removed, 1)

        # TODO: validate effect
        effect = self.wait_for_effect()

        self.assert_graph_eq()

    def test07_create_edge_effect(self):
        # tests the introduction of a new edge by an effect

        # edge without attributes
        q1 = """CREATE ()-[:R]->()"""

        # edge with attributes
        q2 = """CREATE ()-[:connect {v:1}]->()"""

        # edge between an existing node and a new node
        q3 = """MATCH (a) WITH a LIMIT 1 CREATE (a)-[:R]->()"""

        # edge between two existing nodes
        q4 = """MATCH (a), (b) WITH a, b LIMIT 1 CREATE (a)-[:R]->(b)"""

        queries = [q1, q2, q3, q4]
        for q in queries:
            result = self.master_graph.query(q)
            self.env.assertEquals(result.relationships_created, 1)

            # TODO: validate effect
            effect = self.wait_for_effect()

        self.assert_graph_eq()

    def test08_delete_edge_effect(self):
        # test the deletion of an edge by an effect
        q = """MATCH ()-[e]->() WITH e LIMIT 1 DELETE e"""
        result = self.master_graph.query(q)
        self.env.assertEquals(result.relationships_deleted, 1)

        # TODO: validate effect
        effect = self.wait_for_effect()

        self.assert_graph_eq()

    def test09_delete_node_effect(self):
        # test the deletion of a node by an effect
        q = "MATCH (n) DELETE n"
        self.master_graph.query(q)

        # TODO: validate effect
        effect = self.wait_for_effect()

        self.assert_graph_eq()

