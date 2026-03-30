from lxml import etree


def get_or_insert_child(node: etree.Element, name: str, defaulttext='') -> etree.Element:
    """Get a child from the tree if it exists or add it if it doesn't."""
    child = node.find(name)
    if child is None:
        child = etree.Element(name)
        if defaulttext is not None:
            child.text = defaulttext
        node.append(child)
    return child


def elem(name: str, text: str) -> etree.Element:
    """Utility to quicly create a node and assign it text."""
    node = etree.Element(name)
    node.text = text
    return node
