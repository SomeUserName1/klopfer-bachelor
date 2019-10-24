package kn.uni.dbis.neo4j.conceptual.algos.cobweb;

public class ConceptValue implements Value {
    private ConceptNode concept;

    public ConceptValue(ConceptNode node) {
        this.concept = node;
    }

    @Override
    public Value clone() {
        try {
            super.clone();
        } catch (final CloneNotSupportedException e) {
            e.printStackTrace();
        }
        return new ConceptValue(this.concept.clone());
    }

    @Override
    public boolean equals(Object o) {
        if (o instanceof ConceptNode) {
            return ((ConceptNode)o).equals(this.concept);
        } else if (o instanceof ConceptValue) {
            return ((ConceptValue)o).concept.equals(this.concept);
        } else {
            return false;
        }
    }
}
