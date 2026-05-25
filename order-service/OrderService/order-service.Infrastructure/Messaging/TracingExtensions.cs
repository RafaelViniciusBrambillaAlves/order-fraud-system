using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using OpenTelemetry;
using OpenTelemetry.Context.Propagation;
using RabbitMQ.Client;

namespace order_service.Infrastructure.Messaging
{   
    // Helpers para injetar e extrair o trace context nos headers
    public static class TracingExtensions
    {
        private static readonly TextMapPropagator Propagator = 
            Propagators.DefaultTextMapPropagator;

        // Injeta o trace context atual nos headers da mensagem 
        public static void InjectTraceContext(this IBasicProperties properties)
        {
            properties.Headers ??= new Dictionary<string, object>();

            Propagator.Inject(
                new PropagationContext(
                    Activity.Current?.Context ?? default,
                    Baggage.Current),
                properties,
                InjectHeader);
        }

        // Extrai o trace context dos headers de uma mensagem recebida
        public static PropagationContext ExtractTraceContext(
            this IDictionary<string, object>? headers)
        {
            if (headers == null)
                return default;
            
            return Propagator.Extract(
                default,
                headers,
                ExtractHeader);
        }

        // Callback que o propagador usa para escrever um header
        private static void InjectHeader(
            IBasicProperties properties,
            string key, 
            string value)
        {
            properties.Headers![key] = Encoding.UTF8.GetBytes(value);     
        }

        // Callback que o propagador usa para ler um header
        private static IEnumerable<string> ExtractHeader(
            IDictionary<string, object> headers, 
            string key)
        {
            if (!headers.TryGetValue(key, out var value))
                return Enumerable.Empty<string>();

            return value is byte[] bytes 
                ? new[] { Encoding.UTF8.GetString(bytes) }
                : new[] { value.ToString()! };
        } 
    }
}
