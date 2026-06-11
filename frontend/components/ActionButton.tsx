"use client";

import { motion } from "framer-motion";
import type { HTMLMotionProps } from "framer-motion";
import type { ReactNode } from "react";

type ActionButtonProps = HTMLMotionProps<"button"> & {
  icon: ReactNode;
  label: string;
  tone?: "dark" | "light" | "accent";
};

const toneClassNames = {
  dark: "bg-[#ff6b5f] text-white shadow-[#ff6b5f33] hover:bg-[#f2554b]",
  light: "border border-black/10 bg-white/80 text-[#111111] hover:bg-white",
  accent: "bg-[#ff6b5f] text-white shadow-[#ff6b5f33] hover:bg-[#f2554b]",
};

export function ActionButton({
  icon,
  label,
  tone = "light",
  className = "",
  ...props
}: ActionButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: 0.94 }}
      className={`inline-flex h-10 items-center justify-center gap-2 rounded-full px-4 text-sm font-medium shadow-sm transition disabled:cursor-not-allowed disabled:opacity-60 ${toneClassNames[tone]} ${className}`}
      {...props}
    >
      {icon}
      <span>{label}</span>
    </motion.button>
  );
}
