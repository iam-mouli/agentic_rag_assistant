import { DocUpload } from "@/components/docs/doc-upload";
import { DocList } from "@/components/docs/doc-list";

export default function DocsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Documents</h1>
        <p className="text-muted-foreground text-sm mt-1">Upload PDFs and manage your knowledge base</p>
      </div>
      <DocUpload />
      <DocList />
    </div>
  );
}
