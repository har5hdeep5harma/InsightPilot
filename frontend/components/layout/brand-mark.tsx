import { ChartNoAxesCombined } from "lucide-react";
import { cn } from "@/lib/utils";

type BrandMarkProps = {
  className?: string;
  iconClassName?: string;
};

export function BrandMark({ className, iconClassName }: BrandMarkProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-black text-white shadow-[0_3px_0_rgba(15,23,42,0.16)]",
        className
      )}
    >
      <ChartNoAxesCombined className={cn("h-5 w-5", iconClassName)} strokeWidth={2.2} />
    </span>
  );
}