using System;

namespace order_service.Application.Settings;

public sealed class SagaTimeoutSettings
{
    public const string Section = "SagaTimeout";
    public TimeSpan FraudAnalysisTimeout { get; set; } = TimeSpan.FromMinutes(5);
    public TimeSpan CheckInterval { get; init; } = TimeSpan.FromMinutes(1);
}
