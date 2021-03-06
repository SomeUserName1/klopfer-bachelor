package kn.uni.dbis.neo4j.conceptual.algos;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Stream;

import org.neo4j.graphdb.Entity;
import org.neo4j.graphdb.Label;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Relationship;

/**
 * The basic data type for the conceptual hierarchy (tree) constructed and used by cobweb.
 *
 * @author Fabian Klopfer &lt;fabian.klopfer@uni-konstanz.de&gt;
 */
public class ConceptNode {
  /**
   * Attribute aggregation over all (sub-)instances of this Concept.
   */
  private final Map<String, List<Value>> attributes = new HashMap<>();

  /**
   * Number of Nodes under this ConceptNode.
   */
  private int count = 1;
  /**
   * Neo4j ID of the Incorporated node..
   */
  private String id = null;

  /**
   * Assigned label.
   */
  private String label = null;

  /**
   * The sub-concepts of this Concept.
   */
  private final ArrayList<ConceptNode> children = new ArrayList<>();
  /**
   * The super-concept of this concept.
   */
  private ConceptNode parent = null;
  /**
   * previously calculated expected attribute prediction probability.
   */
  private float eap;
  /**
   * flag indicating changes since the last expected attribute prediction accuracy computation.
   */
  private boolean altered;

  /**
   * Constructor.
   */
  public ConceptNode() {
    this.altered = true;
  }

  /**
   * Copy constructor.
   *
   * @param node ConceptNode to copy.
   */
  public ConceptNode(final ConceptNode node) {
    this.count = node.count;
    this.id = node.id;
    this.altered = node.altered;
    this.eap = node.eap;

    List<Value> values;
    String attributeName;
    for (Map.Entry<String, List<Value>> attribute : node.attributes.entrySet()) {
      attributeName = attribute.getKey();
      values = new ArrayList<>();
      this.attributes.put(attributeName, values);
      for (Value value : attribute.getValue()) {
        values.add(value.copy());
      }
    }

    this.children.addAll(node.children);
    this.parent = node.parent;
  }

  /**
   * Converts a property container into a Singleton ConceptNode.
   * Orders are ignored, so all lists are converted to sets.
   *
   * @param propertyContainer The property container to parse.
   */
  ConceptNode(final Entity propertyContainer, final boolean labelsOnly) {
    List<Value> values = new ArrayList<>();
    this.altered = true;

    if (propertyContainer instanceof Relationship) {
      final Relationship rel = (Relationship) propertyContainer;
      this.id = Long.toString(rel.getId());
      values.add(new NominalValue(rel.getType().name()));
      this.attributes.put("RelType", values);
    } else if (propertyContainer instanceof Node) {
      final Node mNode = (Node) propertyContainer;
      this.id = Long.toString(mNode.getId());
      for (Label l : mNode.getLabels()) {
        values.add(new NominalValue(l.name()));
      }
      if (!values.isEmpty()) {
        this.attributes.put("Labels", values);
      }
    }

    if (!labelsOnly) {
      // loop over the properties of a N4J node and cast them to a Value
      Object o;
      Object[] arr;
      try {
        for (Map.Entry<String, Object> property : propertyContainer.getAllProperties().entrySet()) {
          values = new ArrayList<>();
          o = property.getValue();
          if (o.getClass().isArray()) {
            arr = (Object[]) o;

            for (Object ob : arr) {
              values.add(Value.cast(ob));
            }
          } else {
            if (property.getKey().equals("id")) {
              values.add(Value.cast(Long.toString((Long) property.getValue())));
            } else {
              values.add(Value.cast(property.getValue()));
            }
          }
          this.attributes.put(property.getKey(), values);
        }

      } catch (final Exception ignored) {
      }
    }
  }

  public ConceptNode root() {
    this.count = 0;
    this.parent = this;

    return this;
  }

  /**
   * Aggregates the count and attributes of the nodes, hosted by this concept.
   *
   * @param node the node to incorporate into the concept.
   */
  public void updateCounts(final ConceptNode node) {
    List<Value> thisValues;
    NumericValue thisNumeric;
    boolean matched;

    this.count = this.count + node.count;
    // loop over the attributes of the node to incorporate
    for (Map.Entry<String, List<Value>> otherAttributes : node.getAttributes().entrySet()) {
      thisValues = this.attributes.get(otherAttributes.getKey());
      // If the attribute is present in this node, check against the present values
      if (thisValues != null) {
        for (Value otherValue : otherAttributes.getValue()) {
          // iterate over values
          if (otherValue instanceof NumericValue) {
            // When encountering a NumericValue, it must be matched with the one present in this node
            matched = false;
            for (Value thisVal : thisValues) {
              // per attribute there is only one NumericValue that accumulates all numeric values.
              if (thisVal instanceof NumericValue) {
                thisNumeric = (NumericValue) thisVal;
                thisNumeric.update(otherValue);
                matched = true;
                break;
              }
            }
            // When there is no NumericValue in this node for the attribute, add the one of the other node
            if (!matched) {
              thisValues.add(otherValue.copy());
            }
          } else {
            final int idx = thisValues.indexOf(otherValue);
            if (idx == -1) {
              thisValues.add(otherValue.copy());
            } else {
              thisValues.get(idx).update(otherValue);
            }
          }
        }
      } else {
        // Else add the attribute and it's properties of the new node as they are
        final List<Value> copies = new ArrayList<>();
        for (Value value : otherAttributes.getValue()) {
          copies.add(value.copy());
        }
        this.attributes.put(otherAttributes.getKey(), copies);
      }
    }
    this.altered = true;
  }

  /**
   * Computes the Expected Attribute Prediction Probability for the current concept node.
   *
   * @return the EAP
   */
  float getExpectedAttributePrediction() {
    if (!this.altered) {
      return this.eap;
    }
    final float noAttributes = this.getAttributes().size();
    if (noAttributes == 0) {
      return 0;
    }
    float exp = 0;
    final float total = this.getCount();
    float intermediate;
    NumericValue num;

    for (Map.Entry<String, List<Value>> attrib : this.getAttributes().entrySet()) {
      for (Value val : attrib.getValue()) {
        if (val instanceof NumericValue) {
          num = (NumericValue) val;
          // 1 + to cope with std < 1 as they grow very large and hurt the probabilistic ansatz, 7 = 4 * sqrt pi that
          // is moved into the inner most sum
          exp += num.getStd() == 0 ? 0 : 1.0f / (7 * (1 + num.getStd()));
        } else {
          intermediate = val.getCount() / total;
          exp += intermediate * intermediate;
        }
      }
    }
    this.eap = exp / noAttributes;
    return this.eap;
  }

  /**
   * Check if the given concept is a superconcept of the current.
   *
   * @param c ConceptNode the candidate concept.
   * @return true if c is the parent of the node or one of it's parent.
   */
  boolean isSuperConcept(final ConceptNode c) {
    if (this.parent == this) {
      return false;
    } else if (this.parent.equals(c)) {
      return true;
    } else {
      return this.parent.isSuperConcept(c);
    }
  }

  /**
   * Getter for the count.
   *
   * @return number of instances and sub-concepts hosted by this concept
   */
  public int getCount() {
    return this.count;
  }

  /**
   * Getter for the Attribute Value aggregation map.
   *
   * @return the map that stores the attributes as strings and possible values with counts as map
   */
  public Map<String, List<Value>> getAttributes() {
    return this.attributes;
  }

  /**
   * Getter for the sub-concepts of this node.
   *
   * @return the sub-concepts of this node
   */
  public List<ConceptNode> getChildren() {
    return this.children;
  }

  /**
   * Add the given ConceptNode as child.
   *
   * @param node the node to add to the children.
   */
  void addChild(final ConceptNode node) {
    this.children.add(node);
  }

  /**
   * Getter for the super-concept.
   *
   * @return the super concept of this node
   */
  public ConceptNode getParent() {
    return this.parent;
  }

  /**
   * Setter for the super-concept.
   *
   * @param parent the super-concept to be set
   */
  void setParent(final ConceptNode parent) {
    this.parent = parent;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;
    ConceptNode that = (ConceptNode) o;
    if (this.count != that.count) return false;
    if (this.attributes.size() != that.attributes.size()) return false;

    final Iterator<Map.Entry<String, List<Value>>> thisAttributes = this.attributes.entrySet().iterator();

    Map.Entry<String, List<Value>> thisEntry;
    List<Value> thatValues;
    while (thisAttributes.hasNext()) {
      thisEntry = thisAttributes.next();
      thatValues = that.attributes.get(thisEntry.getKey());

      if (thatValues == null || thatValues.size() != thisEntry.getValue().size()) return false;

      for (Value val : thisEntry.getValue()) {
        if (!thatValues.contains(val)) return false;
      }
    }
    return true;
  }

  @Override
  public String toString() {
    String id = this.id != null ? " ID: " + this.id : "";
    return "ConceptNode __" + this.label + "__ " + id + " Count: " + this.count + " Attributes: "
        + this.attributes.toString();
  }

  /**
   * Getter for the ID field.
   *
   * @return the ID of the node or null
   */
  public String getId() {
    return this.id;
  }

  /**
   * Returns the label of the superclass that is cutoffLevel steps away from the root.
   *
   * @param cutoffLevel how far the returned concept should be from the root
   * @return the label of a super-concept of the current node
   */
  String getCutoffLabel(final int cutoffLevel) {
    if (this.label.length() < cutoffLevel) {
      return this.label;
    }
    return this.label.substring(0, cutoffLevel);
  }

  /**
   * getter for the label.
   *
   * @return the label of this node
   */
  public String getLabel() {
    return this.label;
  }

  /**
   * setter for the label.
   *
   * @param label the label to be set in this node
   */
  public void setLabel(final String label) {
    this.label = label;
  }

  /**
   * setter for children.
   *
   * @param idx   index
   * @param child to be set
   */
  void setChild(final int idx, final ConceptNode child) {
    this.children.set(idx, child);
  }

  /**
   * removes children.
   *
   * @param child to be removed
   */
  void removeChild(final ConceptNode child) {
    this.children.remove(child);
  }

  /**
   * clears the children.
   */
  void clearChildren() {
    this.children.clear();
  }

  /**
   * Setter for the Id field.
   *
   * @param id id to be set
   */
  public void setId(final String id) {
    this.id = id;
  }

  public ConceptNode getCutoffConcept(int cutoffLevel) {
    List<ConceptNode> trace = new ArrayList<>();
    ConceptNode current = this;
    do {
      trace.add(current);
      current = current.getParent();
    } while (current.getParent() != current);
    return trace.get(cutoffLevel);
  }
}
