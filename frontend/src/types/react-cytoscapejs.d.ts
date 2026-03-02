declare module "react-cytoscapejs" {
  import { ComponentType } from "react";
  const CytoscapeComponent: ComponentType<{
    elements: unknown[];
    style?: Record<string, string | number>;
    stylesheet?: Array<{ selector: string; style: Record<string, unknown> }>;
    layout?: Record<string, unknown>;
    cy?: (cy: unknown) => void;
  }>;
  export default CytoscapeComponent;
}
