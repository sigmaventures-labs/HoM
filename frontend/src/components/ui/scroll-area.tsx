import * as React from "react";

export interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {}

export const ScrollArea = React.forwardRef<HTMLDivElement, ScrollAreaProps>(({ className, style, children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={className}
      style={{ overflowY: "auto", ...style }}
      {...props}
    >
      {children}
    </div>
  );
});
ScrollArea.displayName = "ScrollArea";


