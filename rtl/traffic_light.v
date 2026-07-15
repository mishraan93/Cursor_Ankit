// Traffic light controller (Moore FSM)
//
// Cycles: GREEN -> YELLOW -> RED -> GREEN ...
// Timing is parameterized in clock cycles.

module traffic_light #(
    parameter integer GREEN_CYCLES  = 20,
    parameter integer YELLOW_CYCLES = 5,
    parameter integer RED_CYCLES    = 15
) (
    input  wire clk,
    input  wire rst_n,
    output reg  red,
    output reg  yellow,
    output reg  green
);

    localparam [1:0] S_GREEN  = 2'b00;
    localparam [1:0] S_YELLOW = 2'b01;
    localparam [1:0] S_RED    = 2'b10;

    reg [1:0] state;
    reg [1:0] next_state;
    reg [$clog2(GREEN_CYCLES + 1) - 1:0] green_cnt;
    reg [$clog2(YELLOW_CYCLES + 1) - 1:0] yellow_cnt;
    reg [$clog2(RED_CYCLES + 1) - 1:0] red_cnt;

    wire green_done  = (green_cnt  == GREEN_CYCLES  - 1);
    wire yellow_done = (yellow_cnt == YELLOW_CYCLES - 1);
    wire red_done    = (red_cnt    == RED_CYCLES    - 1);

    // State register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= S_RED;
        else
            state <= next_state;
    end

    // Next-state logic
    always @(*) begin
        next_state = state;

        case (state)
            S_GREEN: begin
                if (green_done)
                    next_state = S_YELLOW;
            end

            S_YELLOW: begin
                if (yellow_done)
                    next_state = S_RED;
            end

            S_RED: begin
                if (red_done)
                    next_state = S_GREEN;
            end

            default: next_state = S_RED;
        endcase
    end

    // Phase counters
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            green_cnt  <= '0;
            yellow_cnt <= '0;
            red_cnt    <= '0;
        end else begin
            case (state)
                S_GREEN: begin
                    if (green_done)
                        green_cnt <= '0;
                    else
                        green_cnt <= green_cnt + 1'b1;
                end

                S_YELLOW: begin
                    if (yellow_done)
                        yellow_cnt <= '0;
                    else
                        yellow_cnt <= yellow_cnt + 1'b1;
                end

                S_RED: begin
                    if (red_done)
                        red_cnt <= '0;
                    else
                        red_cnt <= red_cnt + 1'b1;
                end

                default: begin
                    green_cnt  <= '0;
                    yellow_cnt <= '0;
                    red_cnt    <= '0;
                end
            endcase
        end
    end

    // Output logic (one-hot style lights)
    always @(*) begin
        red    = 1'b0;
        yellow = 1'b0;
        green  = 1'b0;

        case (state)
            S_GREEN:  green  = 1'b1;
            S_YELLOW: yellow = 1'b1;
            S_RED:    red    = 1'b1;
            default:  red    = 1'b1;
        endcase
    end

endmodule
