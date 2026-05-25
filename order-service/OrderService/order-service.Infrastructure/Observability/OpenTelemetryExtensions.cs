using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using order_service.Application.Observability;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace order_service.Infrastructure.Observability
{
    public static class OpenTelemetryExtensions
    {
        // Nome do ActivitySource que é o "tracer" do .NET
        public const string ServiceName = "order-service";
        public const string ServiceVersion = "1.0.0";

        private static readonly HashSet<string> ExcludedPaths = new(StringComparer.OrdinalIgnoreCase)
        {
             "/health",
            "/metrics",
            "/openapi.json",
            "/favicon.ico",
        };

        private static readonly string[] ExcludedPrefixes = new[]
        {
            "/swagger",
            "/static",
        };

        public static IServiceCollection AddObservability(
            this IServiceCollection services,
            IConfiguration configuration
        )
        {   
            // Lembrar de tirar o HardCode
            var otlpEndpoint = configuration["Observability:OtlpEndpoint"]
                ?? "http://localhost:4317";

            services
                .AddOpenTelemetry()
                .ConfigureResource(resource =>
                {
                    // Atributos de todos os spans
                    resource.AddService(
                        serviceName: ServiceName,
                        serviceVersion: ServiceVersion);

                    resource.AddAttributes(new Dictionary<string, object>
                    {
                        ["deployment.environment"] =
                            Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT") ?? "development",
                    });
                })
                .WithTracing(tracing =>
                {
                    tracing
                        // captura spans de toda request HTTP entrada
                        .AddAspNetCoreInstrumentation(options =>
                        {
                            // Filtra o health check para não gerar spans desnecessários
                            options.Filter = ctx =>
                            {
                                var path = ctx.Request.Path.Value ?? string.Empty;
    
                                if (ExcludedPaths.Contains(path))
                                    return false;
    
                                foreach (var prefix in ExcludedPrefixes)
                                    if (path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                                        return false;
    
                                return true;
                            };

                            // Adiciona atributos uteis no span request
                            options.EnrichWithHttpRequest = (activity, request) =>
                            {
                                activity.SetTag("http.request.body.size",
                                    request.ContentLength);
                            };

                            options.EnrichWithHttpResponse = (activity, response) =>
                            {
                                activity.SetTag("http.response.status_code",
                                    response.StatusCode);
                            };

                            // Marca spans 4xx / 5xx como erro
                            options.RecordException = true;
                        })

                        // captura spans de chamadas HttpClient
                        .AddHttpClientInstrumentation()

                        .AddEntityFrameworkCoreInstrumentation(options =>
                        {
                            options.SetDbStatementForText = true;
                            options.SetDbStatementForStoredProcedure = true;
                        })

                        // ActivitySource customizado   
                        .AddSource(ApplicationTelemetry.ServiceName)

                        // Exporta os spans para um collector OTLP
                        .AddOtlpExporter(options =>
                        {
                            options.Endpoint = new Uri(otlpEndpoint);

                            options.Protocol = 
                                OpenTelemetry.Exporter.OtlpExportProtocol.Grpc;
                        });
                })
                .WithMetrics(metrics =>
                {
                    metrics
                        // Métricas automáticas do ASP.NET Core
                        .AddAspNetCoreInstrumentation()

                        // Métricas automáticas HttpClient
                        .AddHttpClientInstrumentation()

                        // Métricas do runtime: GC, heap, threads, CPU
                        .AddRuntimeInstrumentation()

                        //Nosso Meter customizado
                        .AddMeter(ServiceName)

                        // Exporta para o OTEL Collector
                        .AddOtlpExporter(options =>
                        {
                            options.Endpoint = new Uri(otlpEndpoint);

                            options.Protocol = 
                                OpenTelemetry.Exporter.OtlpExportProtocol.Grpc;
                        });
                });

            return services;
        }
    }
}
