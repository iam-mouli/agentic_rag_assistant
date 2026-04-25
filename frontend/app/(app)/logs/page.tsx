import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AppLogsTab } from "@/components/logs/app-logs-tab";
import { TracesTab } from "@/components/logs/traces-tab";
import { IngestionTab } from "@/components/logs/ingestion-tab";

export default function LogsPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Logs</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Structured application logs, LangSmith traces, and ingestion job history
        </p>
      </div>

      <Tabs defaultValue="app">
        <TabsList>
          <TabsTrigger value="app">Application Logs</TabsTrigger>
          <TabsTrigger value="traces">LangSmith Traces</TabsTrigger>
          <TabsTrigger value="ingestion">Ingestion Jobs</TabsTrigger>
        </TabsList>

        <TabsContent value="app">
          <AppLogsTab />
        </TabsContent>
        <TabsContent value="traces">
          <TracesTab />
        </TabsContent>
        <TabsContent value="ingestion">
          <IngestionTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
