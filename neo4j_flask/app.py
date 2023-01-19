from flask import Flask, jsonify, request
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

uri = os.getenv('URI')
user = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
driver = GraphDatabase.driver(uri, auth=(user, password), database="neo4j")


def initialize_project(tx):
    query = "CREATE (:Employee) " \
            "CREATE (:Department) " \
            "CREATE (:Employee)-[:WORKS_IN]->(:Department) " \
            "CREATE (:Employee)-[:MANAGES]->(:Department)" \
            "CREATE (:Employee {name:'John Doe', position:'Manager'});" \
            "CREATE (:Department {name:'Marketing'});" \
            "MATCH (e:Employee),(d:Department) WHERE e.name = 'John Doe' AND d.name = 'Marketing' " \
            "CREATE (e)-[:WORKS_IN]->(d);"
    tx.run(query)


def get_employees(tx):
    query = "MATCH (e: Employee) RETURN e"
    results = tx.run(query).data()
    employees = [{'name': result['e']['name'], 'position': result['e']['position']} for result in results]
    return employees


@app.route('/employees', methods=['GET'])
def get_employees_route():
    with driver.session() as session:
        employees = session.read_transaction(get_employees)

    response = {'employees': employees}
    return jsonify(response)


def add_employee(tx, name, position):
    query = "CREATE (:Employee {name: $name, position: $position})"
    tx.run(query, name=name, position=position)


@app.route('/employees', methods=['POST'])
def add_employee_route():
    name = request.json["name"]
    position = request.json["position"]

    with driver.session() as session:
        session.write_transaction(add_employee, name, position)

    response = {'status': 'success'}
    return jsonify(response)


def update_employee(tx, id,  name, position):
    query = "MATCH (e:Employee) WHERE id(e) = $id RETURN e"
    result = tx.run(query, id=id).data()

    if not result:
        return None
    else:
        query = "MATCH (e:Employee) " \
                "WHERE id(e) = $id SET e.name = $name, e.position = $position"
        tx.run(query, id=id, name=name, position=position)
        return {'name': name, 'position': position}


@app.route('/employees/<id>', methods=['PUT'])
def update_employee_route(id):
    name = request.json["name"]
    position = request.json["position"]

    with driver.session() as session:
        employee = session.write_transaction(update_employee, id,  name, position)

    if not employee:
        response = {'message': 'Employee not found'}
        return jsonify(response), 404
    else:
        response = {'status': 'success'}
        return jsonify(response)


def delete_employee(tx, id):
    query = "MATCH (e:Employee) WHERE id(e) = $id RETURN e"
    result = tx.run(query, id=id).data()

    if not result:
        return None
    else:
        query = "MATCH (e:Employee)-[:MANAGES]->(d: Department)" \
                " WHERE id(e) = $id RETURN d"
        result = tx.run(query, id=id).data()
        if not result:
            query = "MATCH (e:Employee) WHERE id(e) = $id DETACH DELETE m"
            tx.run(query, id=id)
            return {'id': id}
        else:
            query = "MATCH (e:Employee)-[:MANAGES]->(d: Department)" \
                    " WHERE id(e) = $id " \
                    "DETACH DELETE e, d"
            tx.run(query, id=id)
            return {'id': id}


@app.route('/employees/<id>', methods=['DELETE'])
def delete_employee_route(id):
    with driver.session() as session:
        employee = session.write_transaction(delete_employee, id)

    if not employee:
        response = {'message': 'Employee not found'}
        return jsonify(response), 404
    else:
        response = {'status': 'success'}
        return jsonify(response)


def get_subordinates(tx, id):
    query = "MATCH (e:Employee)-[:WORKS_IN]->(d:Department)" \
            " WHERE id(d) = $id RETURN e"
    result = tx.run(query, id=id)
    subordinates = [record["s"] for record in result]
    return jsonify(subordinates)


@app.route("/employees/<id>/subordinates", methods=['GET'])
def get_subordinates_route(id):
    with driver.session() as session:
        employees = session.read_transaction(get_subordinates, id)

    response = {'employees': employees}
    return jsonify(response)


def get_employee_department(tx, id):
    query = "MATCH (e:Employee)-[:WORKS_IN]->(d:Department)" \
            " WHERE id(d) = $id RETURN e"
    result = tx.run(query, id=id)
    subordinates = [record["e"] for record in result]
    return jsonify(subordinates)


@app.route("/employees/<id>/department", methods=["GET"])
def get_employee_department_route(id):
    with driver.session() as session:
        department = session.read_transaction(get_employee_department, id)

    response = {'department': department}
    return jsonify(response)


def get_departments(tx):
    query = "MATCH (d:Department) RETURN d"
    results = tx.run(query).data()
    employees = [{'name': result['d']['name']} for result in results]
    return employees


@app.route('/departments', methods=['GET'])
def get_departments_route():
    with driver.session() as session:
        departments = session.read_transaction(get_departments)

    response = {'departments': departments}
    return jsonify(response)


def get_department_employees(tx, id):
    query = "MATCH (e:Employee)-[:WORKS_IN]->(d:Department), (e2: Employee)-[:MANAGES]->(d:Department)" \
            " WHERE id(e2) = $id RETURN e"
    results = tx.run(query, id=id).data()
    employees = [{'name': result['e']['name'], 'position': result['e']['position']} for result in results]
    return employees


@app.route('/departments/<id>/employees', methods=['GET'])
def get_department_employees_route(id):
    with driver.session() as session:
        employees = session.read_transaction(get_department_employees, id)

    response = {'employees': employees}
    return jsonify(response)


if __name__ == '__main__':
    app.run()
