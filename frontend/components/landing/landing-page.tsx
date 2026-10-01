"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Database,
  FileSpreadsheet,
  FileText,
  LineChart,
  SearchCheck,
  ShieldCheck,
  TableProperties
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { BrandMark } from "@/components/layout/brand-mark";
import { StatusBadge } from "@/components/ui/status-badge";
import { cn } from "@/lib/utils";

const fadeUp = {
  initial: { opacity: 0, y: 18 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.45, ease: [0.2, 0, 0, 1] }
};

const workflow = [
  {
    title: "Upload",
    description: "Bring a CSV or XLSX file into the local analysis pipeline.",
    icon: FileSpreadsheet
  },
  {
    title: "Profile",
    description: "Detect types, roles, missingness, duplicates, and quality risks.",
    icon: SearchCheck
  },
  {
    title: "Recommend",
    description: "Generate chart specs only when the data supports them.",
    icon: BarChart3
  },
  {
    title: "Explain",
    description: "Create insights with calculation-backed evidence objects.",
    icon: ShieldCheck
  },
  {
    title: "Report",
    description: "Assemble a polished executive memo from verified facts.",
    icon: FileText
  }
];

const features = [
  "CSV and XLSX upload",
  "Column role detection",
  "Dataset health scoring",
  "Missing and duplicate detection",
  "Outlier and correlation analysis",
  "Chart recommendations",
  "Evidence-backed insight cards",
  "Executive memo generation"
];

const audiences = [
  "Business analysts",
  "Consultants",
  "Founders",
  "Marketing teams",
  "Operators",
  "Students working with datasets"
];

const pricing = [
  {
    name: "Local MVP",
    price: "Included",
    description: "Run InsightPilot locally with SQLite and deterministic analytics.",
    status: "Available"
  },
  {
    name: "Pro",
    price: "Preview",
    description: "Future hosted workspace with saved analyses and export workflows.",
    status: "Planned"
  },
  {
    name: "Team",
    price: "Preview",
    description: "Future collaboration layer for shared reports and review cycles.",
    status: "Planned"
  }
];

export function LandingPage() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <LandingNav />
      <HeroSection />
      <ProductPreviewSection />
      <WhySection />
      <WorkflowSection />
      <FeaturesSection />
      <ReportPreviewSection />
      <AudienceSection />
      <PricingSection />
      <FinalCtaSection />
    </main>
  );
}

function LandingNav() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/86">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-3">
          <BrandMark />
          <span className="text-body-sm font-semibold">InsightPilot</span>
        </Link>
        <nav className="hidden items-center gap-6 text-body-sm text-muted-foreground md:flex">
          <Link href="#preview" className="transition-colors hover:text-foreground">
            Preview
          </Link>
          <Link href="#how-it-works" className="transition-colors hover:text-foreground">
            Workflow
          </Link>
          <Link href="#pricing" className="transition-colors hover:text-foreground">
            Pricing
          </Link>
        </nav>
        <Button asChild size="sm">
          <Link href="/studio#ingest">
            Analyze a dataset
            <ArrowRight className="ml-2 h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </Button>
      </div>
    </header>
  );
}

function HeroSection() {
  return (
    <section className="relative overflow-hidden border-b">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-7xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(420px,1.1fr)] lg:px-8">
        <motion.div {...fadeUp} className="max-w-3xl">
          <StatusBadge tone="info">Report-first data analysis</StatusBadge>
          <h1 className="mt-6 max-w-4xl text-display-md font-semibold text-foreground sm:text-display-lg">
            Turn spreadsheets into executive-grade analysis reports.
          </h1>
          <p className="mt-6 max-w-2xl text-body text-muted-foreground sm:text-[1.05rem] sm:leading-8">
            InsightPilot profiles your data, recommends charts, surfaces evidence-backed
            insights, and generates a polished decision memo in minutes.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="default">
              <Link href="/studio#ingest">
                Analyze a dataset
                <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="default">
              <Link href="/studio#ingest">Try sample dataset</Link>
            </Button>
          </div>
          <div className="mt-8 grid max-w-2xl gap-3 text-caption text-muted-foreground sm:grid-cols-3">
            <span className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
              No fake insights
            </span>
            <span className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
              Deterministic evidence
            </span>
            <span className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
              Local MVP ready
            </span>
          </div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.55, ease: [0.2, 0, 0, 1], delay: 0.08 }}
          className="hidden lg:block"
        >
          <StudioPreviewVisual />
        </motion.div>
      </div>
    </section>
  );
}

function ProductPreviewSection() {
  return (
    <SectionFrame
      id="preview"
      eyebrow="Product preview"
      title="Built around the memo, not another dashboard grid."
      description="The product surface is designed to move from data intake to defensible recommendations, with charts and evidence kept close to the narrative."
    >
      <StudioPreviewVisual compact />
    </SectionFrame>
  );
}

function WhySection() {
  const points = [
    ["Dashboards stop at visuals", "Charts rarely explain what changed, why it matters, or what to do next."],
    ["Spreadsheets hide quality risk", "Missing data, duplicate rows, and weak columns often sit underneath confident-looking summaries."],
    ["AI wrappers overpromise", "A useful analysis tool should compute evidence first and only polish language after facts are known."]
  ];

  return (
    <SectionFrame
      eyebrow="Why spreadsheets fail"
      title="Most analysis breaks between chart creation and decision quality."
      description="InsightPilot focuses on the analytical middle layer: profiling, evidence, prioritization, and memo-ready communication."
    >
      <div className="grid gap-4 md:grid-cols-3">
        {points.map(([title, description]) => (
          <motion.article
            key={title}
            {...fadeUp}
            className="rounded-lg border bg-surface p-5 shadow-panel"
          >
            <h3 className="text-heading-sm font-semibold">{title}</h3>
            <p className="mt-3 text-body-sm text-muted-foreground">{description}</p>
          </motion.article>
        ))}
      </div>
    </SectionFrame>
  );
}

function WorkflowSection() {
  return (
    <SectionFrame
      id="how-it-works"
      eyebrow="How InsightPilot works"
      title="A deterministic pipeline from raw file to decision memo."
      description="Every step has a clear input and output, so the report remains auditable."
    >
      <div className="grid gap-3 lg:grid-cols-5">
        {workflow.map((step, index) => {
          const Icon = step.icon;

          return (
            <motion.article
              key={step.title}
              {...fadeUp}
              transition={{ ...fadeUp.transition, delay: index * 0.04 }}
              className="rounded-lg border bg-surface p-5 shadow-panel"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-md border bg-surface-raised text-muted-foreground">
                <Icon className="h-4 w-4" aria-hidden="true" />
              </div>
              <p className="mt-5 text-caption font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Step {index + 1}
              </p>
              <h3 className="mt-2 text-heading-sm font-semibold">{step.title}</h3>
              <p className="mt-3 text-body-sm text-muted-foreground">{step.description}</p>
            </motion.article>
          );
        })}
      </div>
    </SectionFrame>
  );
}

function FeaturesSection() {
  return (
    <SectionFrame
      eyebrow="Features"
      title="The MVP covers the full analytical chain."
      description="The local app connects upload, profiling, chart recommendations, insight review, report preview, and export flows to real backend data."
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((feature) => (
          <motion.div
            key={feature}
            {...fadeUp}
            className="flex items-center gap-3 rounded-lg border bg-surface px-4 py-3 text-body-sm font-medium shadow-panel"
          >
            <CheckCircle2 className="h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
            {feature}
          </motion.div>
        ))}
      </div>
    </SectionFrame>
  );
}

function ReportPreviewSection() {
  return (
    <SectionFrame
      eyebrow="Example report preview"
      title="A polished memo structure with evidence close at hand."
      description="The preview below shows the report composition InsightPilot renders from persisted report JSON. It avoids invented metrics until a real dataset is loaded."
    >
      <motion.article
        {...fadeUp}
        className="mx-auto max-w-4xl rounded-lg border bg-surface px-6 py-8 shadow-panel sm:px-10 sm:py-12"
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-5">
          <div>
            <p className="text-caption font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Executive memo
            </p>
            <h3 className="mt-2 text-heading-md font-semibold">
              Generated from deterministic profile, insights, and chart specs
            </h3>
          </div>
          <StatusBadge tone="success">Evidence required</StatusBadge>
        </div>
        <div className="mt-7 grid gap-6 md:grid-cols-[0.75fr_1.25fr]">
          <aside className="space-y-3 text-body-sm text-muted-foreground">
            {["Dataset overview", "Key findings", "Risks", "Recommended actions", "Evidence appendix"].map((item) => (
              <div key={item} className="rounded-md border bg-surface-raised px-3 py-2">
                {item}
              </div>
            ))}
          </aside>
          <div className="space-y-5">
            <ReportLine title="Executive summary" detail="Concise synthesis of the strongest evidence-backed insights." />
            <ReportLine title="Key findings" detail="Findings reference insight IDs and the calculations that produced them." />
            <ReportLine title="Recommended actions" detail="Actions are practical and cautious when the evidence is limited." />
          </div>
        </div>
      </motion.article>
    </SectionFrame>
  );
}

function AudienceSection() {
  return (
    <SectionFrame
      eyebrow="Who it is for"
      title="For people who need to explain data, not just display it."
      description="InsightPilot is shaped for recurring analysis work where clarity, evidence, and presentation quality matter."
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {audiences.map((audience) => (
          <motion.div
            key={audience}
            {...fadeUp}
            className="rounded-lg border bg-surface p-5 shadow-panel"
          >
            <p className="text-body-sm font-semibold">{audience}</p>
          </motion.div>
        ))}
      </div>
    </SectionFrame>
  );
}

function PricingSection() {
  return (
    <SectionFrame
      id="pricing"
      eyebrow="Pricing preview"
      title="Simple now, extensible later."
      description="The current product is a local MVP. Hosted pricing is intentionally presented as a preview until billing exists."
    >
      <div className="grid gap-4 lg:grid-cols-3">
        {pricing.map((plan) => (
          <motion.article
            key={plan.name}
            {...fadeUp}
            className={cn(
              "rounded-lg border bg-surface p-6 shadow-panel",
              plan.status === "Available" && "border-foreground"
            )}
          >
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-heading-sm font-semibold">{plan.name}</h3>
              <StatusBadge tone={plan.status === "Available" ? "success" : "neutral"}>
                {plan.status}
              </StatusBadge>
            </div>
            <p className="mt-5 text-heading-md font-semibold">{plan.price}</p>
            <p className="mt-3 text-body-sm text-muted-foreground">{plan.description}</p>
          </motion.article>
        ))}
      </div>
    </SectionFrame>
  );
}

function FinalCtaSection() {
  return (
    <section className="border-t bg-surface-inverse text-primary-foreground">
      <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-16 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <div className="max-w-2xl">
          <p className="text-caption font-medium uppercase tracking-[0.16em] text-primary-foreground/60">
            Ready for the studio
          </p>
          <h2 className="mt-4 text-heading-lg font-semibold">
            Move from raw spreadsheet to analyst-grade memo.
          </h2>
          <p className="mt-4 text-body text-primary-foreground/70">
            Start with the upload surface, inspect the evidence, and export a report that
            can be reviewed without trusting unsupported claims.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button asChild variant="secondary">
            <Link href="/studio#ingest">Analyze a dataset</Link>
          </Button>
          <Button asChild variant="outline" className="border-white/20 bg-transparent text-white hover:bg-white/10">
            <Link href="/studio#ingest">Try sample dataset</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}

function SectionFrame({
  id,
  eyebrow,
  title,
  description,
  children
}: {
  id?: string;
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="border-b py-16 sm:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div {...fadeUp} className="mb-8 max-w-3xl">
          <p className="text-caption font-medium uppercase tracking-[0.16em] text-muted-foreground">
            {eyebrow}
          </p>
          <h2 className="mt-3 text-heading-lg font-semibold text-foreground sm:text-display-md">
            {title}
          </h2>
          <p className="mt-4 text-body text-muted-foreground">{description}</p>
        </motion.div>
        {children}
      </div>
    </section>
  );
}

function StudioPreviewVisual({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-surface shadow-panel",
        compact ? "mx-auto max-w-5xl" : "w-full"
      )}
      aria-label="InsightPilot product preview mock area"
    >
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-red-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
        </div>
        <span className="text-caption text-muted-foreground">InsightPilot studio preview</span>
      </div>
      <div className="grid min-h-[430px] lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="hidden border-r bg-surface-raised p-4 lg:block">
          <div className="mb-6 flex items-center gap-2">
            <Database className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <span className="text-body-sm font-semibold">Analysis run</span>
          </div>
          {["Upload", "Profile", "Charts", "Insights", "Memo"].map((item, index) => (
            <div
              key={item}
              className={cn(
                "mb-2 rounded-md px-3 py-2 text-body-sm",
                index === 4 ? "bg-surface text-foreground shadow-hairline" : "text-muted-foreground"
              )}
            >
              {item}
            </div>
          ))}
        </aside>
        <div className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-caption font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Executive memo
              </p>
              <h3 className="mt-2 text-heading-md font-semibold">Decision-ready report</h3>
            </div>
            <StatusBadge tone="success">Evidence checked</StatusBadge>
          </div>
          <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_0.85fr]">
            <div className="rounded-lg border bg-surface-raised p-4">
              <div className="flex items-center gap-2 text-body-sm font-semibold">
                <FileText className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                Report sections
              </div>
              <div className="mt-4 space-y-3">
                {["Dataset overview", "Key findings", "Risks", "Recommended actions"].map((item) => (
                  <div key={item} className="rounded-md border bg-surface px-3 py-3">
                    <p className="text-body-sm font-medium">{item}</p>
                    <div className="mt-2 h-2 w-full rounded-full bg-secondary" />
                    <div className="mt-2 h-2 w-2/3 rounded-full bg-secondary" />
                  </div>
                ))}
              </div>
            </div>
            <div className="space-y-4">
              <div className="rounded-lg border bg-surface p-4">
                <div className="flex items-center gap-2 text-body-sm font-semibold">
                  <LineChart className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                  Recommended chart
                </div>
                <div className="mt-5 flex h-32 items-end gap-2 border-b border-l px-3">
                  {[34, 56, 48, 72, 58, 86, 64].map((height) => (
                    <span
                      key={height}
                      className="flex-1 rounded-t-sm bg-accent/45"
                      style={{ height }}
                    />
                  ))}
                </div>
              </div>
              <div className="rounded-lg border bg-surface p-4">
                <div className="flex items-center gap-2 text-body-sm font-semibold">
                  <TableProperties className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                  Evidence appendix
                </div>
                <p className="mt-3 text-body-sm text-muted-foreground">
                  Calculations, related columns, row counts, and explanations stay attached
                  to every insight.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReportLine({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="border-b pb-4 last:border-b-0 last:pb-0">
      <p className="text-body-sm font-semibold">{title}</p>
      <p className="mt-2 text-body-sm text-muted-foreground">{detail}</p>
    </div>
  );
}
