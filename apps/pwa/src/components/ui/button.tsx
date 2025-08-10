import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-electric-violet focus-visible:ring-offset-2 focus-visible:ring-offset-black disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-electric-violet text-white hover:bg-electric-violet/90 hover:shadow-lg hover:shadow-electric-violet/25 active:scale-[0.98]",
        secondary: "bg-deep-purple text-white hover:bg-deep-purple/90 hover:shadow-lg hover:shadow-deep-purple/25",
        destructive: "bg-red-500 text-white hover:bg-red-600 hover:shadow-lg hover:shadow-red-500/25",
        outline: "border border-electric-violet/30 bg-transparent text-white hover:bg-electric-violet/10 hover:border-electric-violet/50",
        ghost: "text-white hover:bg-white/10 hover:text-electric-violet",
        link: "text-electric-violet underline-offset-4 hover:underline hover:text-electric-violet/80",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }